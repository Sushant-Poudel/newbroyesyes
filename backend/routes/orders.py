"""Order creation, payment, completion, status, tracking, and invoice routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import db, DISCORD_ORDER_WEBHOOK
from dependencies import get_current_user, get_current_customer, check_permission, create_audit_log
from email_service import send_email, get_order_confirmation_email, get_order_status_update_email
from discord_service import send_discord_order_notification, send_discord_order_status_update, send_discord_test_notification, send_confirmed_order_notification
import google_sheets_service
import uuid
import os
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== MODELS ====================

class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1
    variation: Optional[str] = None
    product_id: Optional[str] = None
    variation_id: Optional[str] = None

class CreateOrderRequest(BaseModel):
    customer_name: str
    customer_email: str
    customer_phone: str
    items: List[OrderItem]
    payment_method: str
    total_amount: float
    promo_code: Optional[str] = None
    discount_amount: float = 0
    whatsapp_number: Optional[str] = None
    credits_used: float = 0
    credit_discount: float = 0

class PaymentScreenshotUpload(BaseModel):
    screenshot_url: str
    payment_method: Optional[str] = None
    payment_note: Optional[str] = None
    sender_name: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None

class BulkDeleteRequest(BaseModel):
    order_ids: List[str]

class WebhookTestRequest(BaseModel):
    webhook_url: str
    message: str = "Test webhook from GameShop Nepal"


# Import credit functions from promotions module
async def _use_credits(customer_email, amount, order_id):
    """Proxy to use_credits - imported lazily to avoid circular imports."""
    from routes.promotions import use_credits
    return await use_credits(customer_email, amount, order_id)

async def _award_credits_for_order(order_id, customer_email, order_total):
    """Proxy to award_credits_for_order - imported lazily to avoid circular imports."""
    from routes.promotions import award_credits_for_order
    return await award_credits_for_order(order_id, customer_email, order_total)

class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1
    variation: Optional[str] = None
    product_id: Optional[str] = None  # For Discord webhook lookup
    variation_id: Optional[str] = None

class CreateOrderRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: str  # Required
    items: List[OrderItem]
    total_amount: float
    remark: Optional[str] = None
    credits_used: float = 0  # Store credits used for this order
    promo_code: Optional[str] = None  # Promo code used for this order

@router.post("/orders/create")
async def create_order(order_data: CreateOrderRequest):
    # Validate required fields
    if not order_data.customer_phone or not order_data.customer_phone.strip():
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not order_data.customer_email or not order_data.customer_email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    
    order_id = str(uuid.uuid4())

    def format_phone_number(phone):
        phone = ''.join(filter(str.isdigit, phone))
        if phone.startswith('0'):
            phone = phone[1:]
        if not phone.startswith('977') and len(phone) == 10:
            phone = '977' + phone
        return phone

    formatted_phone = format_phone_number(order_data.customer_phone)

    items_text = ", ".join([f"{item.quantity}x {item.name}" + (f" ({item.variation})" if item.variation else "") for item in order_data.items])

    local_order = {
        "id": order_id,
        "customer_name": order_data.customer_name,
        "customer_phone": formatted_phone,
        "customer_email": order_data.customer_email,
        "items": [item.model_dump() for item in order_data.items],
        "total_amount": order_data.total_amount,
        "total": order_data.total_amount,  # Also save as 'total' for invoice compatibility
        "remark": order_data.remark,
        "items_text": items_text,
        "status": "pending",
        "payment_screenshot": None,
        "payment_method": None,
        "credits_used": order_data.credits_used,
        "promo_code": order_data.promo_code,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.orders.insert_one(local_order)
    
    # Record promo code usage if a promo was used
    if order_data.promo_code:
        try:
            # Increment usage count
            await db.promo_codes.update_one(
                {"code": order_data.promo_code.upper()},
                {"$inc": {"used_count": 1}}
            )
            
            # Record individual usage
            usage_record = {
                "id": str(uuid.uuid4()),
                "promo_code": order_data.promo_code.upper(),
                "order_id": order_id,
                "customer_email": order_data.customer_email.lower(),
                "used_at": datetime.now(timezone.utc).isoformat()
            }
            await db.promo_usage.insert_one(usage_record)
            logger.info(f"Promo code {order_data.promo_code} usage recorded for order {order_id}")
        except Exception as e:
            logger.error(f"Failed to record promo usage: {e}")
    
    # Don't deduct credits immediately - they will be deducted when order is confirmed
    # Just mark the order with pending credits
    if order_data.credits_used > 0:
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {"credits_pending": True}}
        )
    
    # Sync order to Google Sheets (in background)
    try:
        google_sheets_service.sync_order_to_sheets(local_order)
    except Exception as e:
        logger.warning(f"Failed to sync order to Google Sheets: {e}")

    # Send order confirmation email
    if order_data.customer_email:
        try:
            subject, html, text = get_order_confirmation_email(local_order)
            send_email(order_data.customer_email, subject, html, text)
            logger.info(f"Order confirmation email sent to {order_data.customer_email}")
        except Exception as e:
            logger.error(f"Failed to send order confirmation email: {e}")
    
    # Discord webhook will be sent after payment screenshot upload
    # See /orders/{order_id}/payment-screenshot endpoint

    return {
        "success": True,
        "order_id": order_id,
        "message": "Order created successfully"
    }

@router.get("/orders/new-confirmed-count")
async def get_new_confirmed_count(since: str = None, current_user: dict = Depends(get_current_user)):
    """Get count of confirmed orders since a given timestamp (for admin sound notifications)"""
    query = {"status": "Confirmed"}
    if since:
        query["created_at"] = {"$gt": since}
    count = await db.orders.count_documents(query)
    latest = await db.orders.find_one({"status": "Confirmed"}, {"_id": 0, "created_at": 1}, sort=[("created_at", -1)])
    return {"count": count, "latest_at": latest.get("created_at") if latest else None}


@router.get("/orders")
async def get_local_orders(
    current_user: dict = Depends(get_current_user), 
    limit: int = 1000, 
    skip: int = 0,
    days: Optional[int] = None
):
    """Get orders with optional date filter. Use days=30 for last 30 days."""
    query = {}
    
    # Filter by date if days parameter is provided
    if days:
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        query["created_at"] = {"$gte": from_date.isoformat()}
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Also return total count for pagination info
    total_count = await db.orders.count_documents(query)
    
    return {"orders": orders, "total": total_count, "limit": limit, "skip": skip}


# ==================== ORDER PAYMENT SCREENSHOT ====================

class PaymentScreenshotUpload(BaseModel):
    screenshot_url: str
    payment_method: Optional[str] = None
    payment_sent_to: Optional[str] = None

@router.post("/orders/{order_id}/payment-screenshot")
async def upload_payment_screenshot(order_id: str, data: PaymentScreenshotUpload):
    """Upload payment screenshot for an order - automatically marks as Confirmed and deducts credits"""
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Generate invoice URL
    invoice_url = f"/invoice/{order_id}"
    
    # Deduct store credits if customer used them
    credits_deducted = 0
    customer_email = order.get("customer_email")
    credits_used = float(order.get("credits_used", 0) or 0)
    credits_pending = order.get("credits_pending", False)
    
    logger.info(f"Order {order_id}: email={customer_email}, credits_used={credits_used}, credits_pending={credits_pending}")
    
    if credits_used > 0 and customer_email:
        try:
            await _use_credits(customer_email, credits_used, order_id)
            credits_deducted = credits_used
            logger.info(f"Deducted {credits_used} credits from {customer_email} for order {order_id}")
        except Exception as e:
            logger.warning(f"Failed to deduct credits for order {order_id}: {e}")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "payment_screenshot": data.screenshot_url,
            "payment_method": data.payment_method,
            "payment_sent_to": data.payment_sent_to,
            "payment_uploaded_at": datetime.now(timezone.utc).isoformat(),
            "status": "Confirmed",
            "invoice_url": invoice_url,
            "credits_pending": False,
            "credits_deducted": credits_deducted > 0
        }}
    )
    
    # Send payment screenshot to dedicated webhook
    payment_webhook_url = None
    try:
        wh_settings = await db.site_settings.find_one({"id": "webhook_settings"}, {"_id": 0})
        if wh_settings and wh_settings.get("payment_webhook"):
            payment_webhook_url = wh_settings["payment_webhook"]
    except Exception:
        pass
    if not payment_webhook_url:
        payment_webhook_url = "https://discord.com/api/webhooks/1481673730177372284/ZSwFuiblK2sJ0QaXU45pwsJDaMSZyQQN5_yTYmIWxFnIHI3WVYHPmUYDOfP_ykxpYwE7"
    try:
        import httpx
        order_num = order.get("takeapp_order_number") or order_id[:8]
        customer_name = order.get("customer_name") or "Unknown"
        items_text = order.get("items_text") or ", ".join(i.get("name", "") for i in order.get("items", []))
        total_amt = f"Rs {round(order.get('total_amount', 0)):,}"
        
        embed = {
            "title": f"Payment Screenshot - Order #{order_num}",
            "color": 0xF59E0B,
            "fields": [
                {"name": "Customer", "value": customer_name, "inline": True},
                {"name": "Total", "value": total_amt, "inline": True},
                {"name": "Payment Method", "value": data.payment_method or "Not specified", "inline": True},
                {"name": "Payment Sent To", "value": data.payment_sent_to or "Not specified", "inline": True},
                {"name": "Items", "value": items_text or "N/A", "inline": False},
            ],
            "image": {"url": data.screenshot_url},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        async with httpx.AsyncClient() as client:
            await client.post(payment_webhook_url, json={"embeds": [embed]}, timeout=10)
        logger.info(f"Payment screenshot webhook sent for order {order_id}")
    except Exception as e:
        logger.warning(f"Failed to send payment screenshot webhook: {e}")
    
    # Send Discord webhook notifications for products with webhooks
    try:
        # Get updated order
        updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        
        # Collect all Discord webhooks from order items
        all_webhooks = []
        product_names = []
        
        # Batch fetch all products to avoid N+1 queries
        product_ids = [item.get('product_id') for item in updated_order.get('items', []) if item.get('product_id')]
        if product_ids:
            products = await db.products.find({"id": {"$in": product_ids}}, {"_id": 0, "id": 1, "name": 1, "discord_webhooks": 1}).to_list(len(product_ids))
            product_map = {p['id']: p for p in products}
            
            for item in updated_order.get('items', []):
                product_id = item.get('product_id')
                if product_id and product_id in product_map:
                    product = product_map[product_id]
                    if product.get('discord_webhooks'):
                        all_webhooks.extend(product.get('discord_webhooks', []))
                        product_names.append(product.get('name', 'Unknown'))
        
        # Remove duplicates
        unique_webhooks = list(set([w for w in all_webhooks if w and w.strip()]))
        
        if unique_webhooks:
            logger.info(f"Sending Discord notifications to {len(unique_webhooks)} webhooks for paid order {order_id}")
            await send_discord_order_notification(
                webhook_urls=unique_webhooks,
                order_data=updated_order,
                product_data={"name": ", ".join(set(product_names))} if product_names else None
            )
        
        # Also send to global confirmed order webhook
        global_order_webhook = DISCORD_ORDER_WEBHOOK
        try:
            wh_settings_global = await db.site_settings.find_one({"id": "webhook_settings"}, {"_id": 0})
            if wh_settings_global and wh_settings_global.get("order_webhook"):
                global_order_webhook = wh_settings_global["order_webhook"]
        except Exception:
            pass
        if global_order_webhook:
            await send_confirmed_order_notification(global_order_webhook, updated_order)
            logger.info(f"Sent global Discord notification for confirmed order {order_id}")
    except Exception as e:
        logger.error(f"Failed to send Discord webhook: {e}")
    
    response = {
        "message": "Payment screenshot uploaded", 
        "order_id": order_id,
        "status": "Confirmed",
        "invoice_url": invoice_url
    }
    
    if credits_deducted > 0:
        response["credits_deducted"] = credits_deducted
    
    return response

@router.post("/orders/{order_id}/complete")
async def complete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Mark order as completed, award credits, and send invoice email"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Award credits for this order BEFORE updating status
    customer_email = order.get("customer_email")
    credits_awarded = 0
    if customer_email:
        try:
            # Calculate credits based on order total
            order_total = order.get("total_amount", 0) or order.get("total", 0)
            
            credit_result = await _award_credits_for_order(order_id, customer_email, order_total)
            credits_awarded = credit_result.get("credits_awarded", 0)
            logger.info(f"Awarded {credits_awarded} credits to {customer_email} for order {order_id}")
        except Exception as e:
            logger.warning(f"Failed to award credits for order {order_id}: {e}")
    
    # Update status to Completed with credits info
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "status": "Completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "credits_awarded": credits_awarded
        }}
    )
    
    # Decrement variation stock for each item
    for item in order.get("items", []):
        qty = item.get("quantity", 1)
        product_id = item.get("product_id")
        variation_id = item.get("variation_id")
        variation_name = item.get("variation")
        
        try:
            if product_id and variation_id:
                # Match by product_id + variation_id
                await db.products.update_one(
                    {"id": product_id, "variations.id": variation_id, "variations.stock": {"$gt": 0}},
                    {"$inc": {"variations.$.stock": -qty}}
                )
            elif product_id and variation_name:
                # Match by product_id + variation name
                await db.products.update_one(
                    {"id": product_id, "variations.name": variation_name, "variations.stock": {"$gt": 0}},
                    {"$inc": {"variations.$.stock": -qty}}
                )
            elif variation_name:
                # Legacy: match by item name + variation name across all products
                item_name = item.get("name", "")
                product = await db.products.find_one(
                    {"variations.name": variation_name},
                    {"_id": 0, "id": 1}
                )
                if product:
                    await db.products.update_one(
                        {"id": product["id"], "variations.name": variation_name, "variations.stock": {"$gt": 0}},
                        {"$inc": {"variations.$.stock": -qty}}
                    )
            logger.info(f"Decremented stock for variation '{variation_name or variation_id}' by {qty}")
        except Exception as e:
            logger.warning(f"Failed to decrement stock for item: {e}")
    
    # Send invoice email to customer if email exists
    if customer_email:
        try:
            site_url = os.environ.get("SITE_URL", "https://gameshopnepal.com")
            invoice_url = f"{site_url}/invoice/{order_id}"
            review_url = "https://gameshopnepal.com/reviews"
            
            # Credits message
            credits_message = ""
            if credits_awarded > 0:
                credits_message = f"""
                    <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-radius: 10px; padding: 15px; margin: 20px 0; text-align: center;">
                        <p style="color: #fff; margin: 0; font-size: 16px;">🎉 You earned <strong>Rs {credits_awarded:.0f}</strong> in store credits!</p>
                        <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 13px;">Use it on your next purchase</p>
                    </div>
                """
            
            subject = f"Your Order #{order_id[:8]} is Complete - GameShop Nepal"
            html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #1a1a1a; color: #fff;">
                <div style="background: linear-gradient(135deg, #F5A623 0%, #D4920D 100%); padding: 30px; text-align: center;">
                    <h1 style="margin: 0; color: #000; font-size: 28px;">Order Complete!</h1>
                </div>
                <div style="padding: 30px;">
                    <p style="color: #ccc; font-size: 16px;">Hi {order.get('customer_name', 'Customer')},</p>
                    <p style="color: #ccc; font-size: 16px;">Your order has been completed successfully!</p>
                    
                    {credits_message}
                    
                    <div style="background: #2a2a2a; border-radius: 10px; padding: 20px; margin: 20px 0;">
                        <h2 style="color: #F5A623; margin-top: 0;">Order Summary</h2>
                        <p style="color: #fff;"><strong>Order ID:</strong> #{order_id[:8]}</p>
                        <p style="color: #fff;"><strong>Items:</strong> {order.get('items_text', 'N/A')}</p>
                        <p style="color: #F5A623; font-size: 20px;"><strong>Total:</strong> Rs {order.get('total', order.get('total_amount', 0)):,.0f}</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invoice_url}" style="display: inline-block; background: #F5A623; color: #000; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; margin-right: 10px;">
                            View Invoice
                        </a>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0; padding: 20px; background: #2a2a2a; border-radius: 10px;">
                        <p style="color: #ccc; margin-bottom: 15px;">Enjoyed your experience? We'd love your feedback!</p>
                        <a href="{review_url}" style="display: inline-block; background: #F5A623; color: #000; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Leave a Review
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; text-align: center; margin-top: 30px;">
                        Thank you for shopping with GameShop Nepal!
                    </p>
                </div>
            </div>
            """
            text = f"Order #{order_id[:8]} Complete!\n\nYour order has been completed.\n{'You earned Rs ' + str(int(credits_awarded)) + ' in store credits!' if credits_awarded > 0 else ''}\nView Invoice: {invoice_url}\nLeave a Review: {review_url}"
            
            from email_service import send_email
            send_email(customer_email, subject, html, text)
        except Exception as e:
            print(f"Failed to send invoice email: {e}")
    
    response = {"message": "Order marked as completed", "order_id": order_id}
    if credits_awarded > 0:
        response["credits_awarded"] = credits_awarded
    return response


@router.delete("/orders/{order_id}")
async def delete_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an order - requires delete_orders permission"""
    # Check permission
    if not check_permission(current_user, 'delete_orders'):
        raise HTTPException(status_code=403, detail="You don't have permission to delete orders")
    
    # Check if order exists
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Delete the order
    result = await db.orders.delete_one({"id": order_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete order")
    
    logger.info(f"Order deleted by {current_user.get('username')}: {order_id}")
    
    return {"message": "Order deleted successfully", "order_id": order_id}

class BulkDeleteRequest(BaseModel):
    order_ids: List[str]

@router.post("/orders/bulk-delete")
async def bulk_delete_orders(request: BulkDeleteRequest, current_user: dict = Depends(get_current_user)):
    """Bulk delete orders - requires delete_orders permission"""
    
    if not check_permission(current_user, 'delete_orders'):
        raise HTTPException(status_code=403, detail="You don't have permission to delete orders")
    
    if not request.order_ids:
        raise HTTPException(status_code=400, detail="No order IDs provided")
    
    deleted_count = 0
    failed_ids = []
    
    for order_id in request.order_ids:
        try:
            result = await db.orders.delete_one({"id": order_id})
            if result.deleted_count > 0:
                deleted_count += 1
                # Also delete tracking history
                await db.order_status_history.delete_many({"order_id": order_id})
            else:
                failed_ids.append(order_id)
        except Exception as e:
            logger.error(f"Failed to delete order {order_id}: {e}")
            failed_ids.append(order_id)
    
    logger.info(f"Bulk delete by {current_user.get('username')}: {deleted_count} orders deleted")
    
    return {
        "message": f"Successfully deleted {deleted_count} orders",
        "deleted_count": deleted_count,
        "failed_ids": failed_ids
    }

@router.get("/invoice/{order_id}")
async def get_invoice(order_id: str):
    """Get invoice data for an order"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order": order,
        "invoice_number": f"INV-{order_id[:8].upper()}",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/orders/track/{order_id}")
async def track_order(order_id: str):
    """Public order tracking by order ID or order number"""
    order = await db.orders.find_one(
        {"$or": [
            {"id": order_id}, 
            {"takeapp_order_id": order_id},
            {"takeapp_order_number": order_id}
        ]},
        {"_id": 0}
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get status history
    history = await db.order_status_history.find(
        {"order_id": order.get("id")},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    
    # Mask sensitive data for public view
    return {
        "id": order.get("id"),
        "order_number": order.get("takeapp_order_number"),
        "status": order.get("status", "pending"),
        "items_text": order.get("items_text"),
        "total_amount": order.get("total_amount"),
        "created_at": order.get("created_at"),
        "status_history": history,
        "estimated_delivery": "Instant delivery after payment confirmation"
    }

@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, status_data: OrderStatusUpdate, current_user: dict = Depends(get_current_user)):
    """Admin: Update order status"""
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.get("status", "pending")
    new_status = status_data.status.lower()
    
    # Update order status
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {"status": status_data.status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Add to status history
    history_entry = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "old_status": old_status,
        "new_status": status_data.status,
        "note": status_data.note,
        "updated_by": current_user.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.order_status_history.insert_one(history_entry)
    
    # Create audit log for order status change
    order_number = order.get('takeapp_order_number', order_id[:8].upper())
    await create_audit_log(
        action="UPDATE_ORDER_STATUS",
        actor_id=current_user.get("id"),
        actor_name=current_user.get("name", current_user.get("email")),
        actor_role=current_user.get("role", "admin"),
        resource_type="order",
        resource_id=order_id,
        resource_name=f"Order #{order_number}",
        details={
            "old_status": old_status,
            "new_status": status_data.status,
            "note": status_data.note,
            "customer_email": order.get("customer_email")
        }
    )
    
    credits_deducted = 0
    credits_awarded = 0
    customer_email = order.get("customer_email")
    
    # Deduct credits when order is CONFIRMED (not pending anymore)
    if new_status == "confirmed" and old_status.lower() != "confirmed":
        credits_used = order.get("credits_used", 0)
        if credits_used > 0 and customer_email and order.get("credits_pending"):
            try:
                await _use_credits(customer_email, credits_used, order_id)
                credits_deducted = credits_used
                # Mark credits as deducted
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {"credits_pending": False, "credits_deducted": True}}
                )
                logger.info(f"Deducted {credits_used} credits from {customer_email} for confirmed order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to deduct credits for order {order_id}: {e}")
        
        # Send Discord notification for confirmed order (global webhook)
        global_wh = DISCORD_ORDER_WEBHOOK
        try:
            wh_s = await db.site_settings.find_one({"id": "webhook_settings"}, {"_id": 0})
            if wh_s and wh_s.get("order_webhook"):
                global_wh = wh_s["order_webhook"]
        except Exception:
            pass
        if global_wh:
            try:
                updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
                await send_confirmed_order_notification(global_wh, updated_order)
                logger.info(f"Sent Discord notification for confirmed order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to send Discord notification for order {order_id}: {e}")
    
    # Award credits when order is COMPLETED
    if new_status == "completed" and old_status.lower() != "completed":
        if customer_email:
            try:
                order_total = order.get("total_amount", 0)
                credit_result = await _award_credits_for_order(order_id, customer_email, order_total)
                credits_awarded = credit_result.get("credits_awarded", 0)
                if credits_awarded > 0:
                    logger.info(f"Awarded {credits_awarded} credits to {customer_email} for completed order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to award credits for order {order_id}: {e}")
        
        # Update order with completion timestamp
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {"completed_at": datetime.now(timezone.utc).isoformat(), "credits_awarded": credits_awarded}}
        )
        
        # Decrement variation stock for each item
        for item in order.get("items", []):
            qty = item.get("quantity", 1)
            pid = item.get("product_id")
            vid = item.get("variation_id")
            vname = item.get("variation")
            try:
                if pid and vid:
                    await db.products.update_one(
                        {"id": pid, "variations.id": vid, "variations.stock": {"$gt": 0}},
                        {"$inc": {"variations.$.stock": -qty}}
                    )
                elif pid and vname:
                    await db.products.update_one(
                        {"id": pid, "variations.name": vname, "variations.stock": {"$gt": 0}},
                        {"$inc": {"variations.$.stock": -qty}}
                    )
                elif vname:
                    product = await db.products.find_one({"variations.name": vname}, {"_id": 0, "id": 1})
                    if product:
                        await db.products.update_one(
                            {"id": product["id"], "variations.name": vname, "variations.stock": {"$gt": 0}},
                            {"$inc": {"variations.$.stock": -qty}}
                        )
            except Exception as e:
                logger.warning(f"Failed to decrement stock for item: {e}")
        
        # Send invoice email automatically when marked as completed
        if customer_email:
            try:
                site_url = os.environ.get("SITE_URL", "https://gameshopnepal.com")
                invoice_url = f"{site_url}/invoice/{order_id}"
                review_url = "https://gameshopnepal.com/reviews"
                
                # Credits message
                credits_message = ""
                if credits_awarded > 0:
                    credits_message = f"""
                        <div style="background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-radius: 12px; padding: 18px; margin: 25px 0; text-align: center;">
                            <p style="color: #fff; margin: 0; font-size: 17px; font-weight: 600;">You earned Rs {credits_awarded:.0f} in store credits!</p>
                            <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0 0; font-size: 13px;">Use it on your next purchase</p>
                        </div>
                    """
                
                order_number = order.get('takeapp_order_number', order_id[:8].upper())
                subject = f"Order #{order_number} Complete - Your Invoice | GameShop Nepal"
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                </head>
                <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #050505;">
                    <table role="presentation" width="100%" style="background-color: #050505;">
                        <tr>
                            <td align="center" style="padding: 30px 15px;">
                                <table role="presentation" width="600" style="background: linear-gradient(180deg, #0f0f0f 0%, #0a0a0a 100%); border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(245, 166, 35, 0.1);">
                                    
                                    <!-- Header -->
                                    <tr>
                                        <td style="padding: 28px 40px; background: linear-gradient(135deg, #141414 0%, #0f0f0f 100%); border-bottom: 1px solid rgba(245, 166, 35, 0.15);">
                                            <table role="presentation" width="100%">
                                                <tr>
                                                    <td>
                                                        <div style="display: inline-block; width: 44px; height: 44px; background: linear-gradient(135deg, #F5A623 0%, #E8930C 100%); border-radius: 12px; text-align: center; line-height: 44px; box-shadow: 0 4px 15px rgba(245, 166, 35, 0.3); vertical-align: middle;">
                                                            <span style="font-size: 22px; font-weight: 800; color: #000;">G</span>
                                                        </div>
                                                        <span style="margin-left: 12px; font-size: 22px; font-weight: 800; color: #ffffff; vertical-align: middle;">GameShop Nepal</span>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- Success Hero -->
                                    <tr>
                                        <td style="padding: 50px 40px 40px; text-align: center; background: linear-gradient(180deg, rgba(34, 197, 94, 0.08) 0%, transparent 100%);">
                                            <div style="width: 88px; height: 88px; margin: 0 auto 24px; background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); border-radius: 50%; text-align: center; line-height: 88px; box-shadow: 0 15px 40px rgba(34, 197, 94, 0.35);">
                                                <span style="font-size: 44px; color: #fff; line-height: 88px;">✓</span>
                                            </div>
                                            <h1 style="margin: 0 0 10px; font-size: 30px; font-weight: 800; color: #fff;">Order Complete!</h1>
                                            <p style="margin: 0; font-size: 16px; color: #888;">Thank you for your purchase, <strong style="color: #fff;">{order.get('customer_name', 'Customer')}</strong></p>
                                        </td>
                                    </tr>
                                    
                                    {credits_message}
                                    
                                    <!-- Order Details -->
                                    <tr>
                                        <td style="padding: 0 40px 30px;">
                                            <table role="presentation" width="100%" style="background: linear-gradient(135deg, #141414 0%, #0f0f0f 100%); border-radius: 16px; border: 1px solid rgba(255,255,255,0.06);">
                                                <tr>
                                                    <td style="padding: 24px;">
                                                        <h3 style="margin: 0 0 18px; font-size: 13px; font-weight: 700; color: #888; text-transform: uppercase; letter-spacing: 1px;">Order Summary</h3>
                                                        <table role="presentation" width="100%">
                                                            <tr>
                                                                <td style="padding: 8px 0;"><span style="color: #666;">Order Number</span></td>
                                                                <td align="right"><span style="color: #F5A623; font-weight: 700;">#{order_number}</span></td>
                                                            </tr>
                                                            <tr>
                                                                <td style="padding: 8px 0;"><span style="color: #666;">Items</span></td>
                                                                <td align="right"><span style="color: #fff;">{order.get('items_text', 'N/A')}</span></td>
                                                            </tr>
                                                            <tr>
                                                                <td colspan="2" style="padding-top: 15px;">
                                                                    <div style="height: 1px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);"></div>
                                                                </td>
                                                            </tr>
                                                            <tr>
                                                                <td style="padding-top: 15px;"><span style="color: #fff; font-size: 17px; font-weight: 700;">Total</span></td>
                                                                <td align="right" style="padding-top: 15px;"><span style="color: #F5A623; font-size: 24px; font-weight: 800;">Rs {order.get('total_amount', order.get('total', 0)):,.0f}</span></td>
                                                            </tr>
                                                        </table>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- CTA Buttons -->
                                    <tr>
                                        <td style="padding: 0 40px 35px; text-align: center;">
                                            <a href="{invoice_url}" style="display: inline-block; padding: 16px 36px; background: linear-gradient(135deg, #F5A623 0%, #E8930C 100%); color: #000; text-decoration: none; border-radius: 12px; font-size: 15px; font-weight: 700; box-shadow: 0 8px 25px rgba(245, 166, 35, 0.3);">
                                                View Invoice
                                            </a>
                                        </td>
                                    </tr>
                                    
                                    <!-- Review Request -->
                                    <tr>
                                        <td style="padding: 0 40px 40px;">
                                            <table role="presentation" width="100%" style="background: linear-gradient(135deg, rgba(0, 182, 122, 0.08) 0%, rgba(0, 182, 122, 0.03) 100%); border-radius: 16px; border: 1px solid rgba(0, 182, 122, 0.15);">
                                                <tr>
                                                    <td style="padding: 25px; text-align: center;">
                                                        <p style="margin: 0 0 15px; font-size: 15px; color: #bbb;">Enjoyed your experience? We'd love your feedback!</p>
                                                        <a href="{review_url}" style="display: inline-block; padding: 14px 28px; background: linear-gradient(135deg, #F5A623 0%, #D4920D 100%); color: #000; text-decoration: none; border-radius: 10px; font-size: 14px; font-weight: 600;">
                                                            Leave a Review
                                                        </a>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- Footer -->
                                    <tr>
                                        <td style="padding: 30px 40px; background: linear-gradient(180deg, #0a0a0a 0%, #050505 100%); border-top: 1px solid rgba(255,255,255,0.05); text-align: center;">
                                            <p style="margin: 0 0 10px; font-size: 12px; color: #555;">Questions? Chat with us on WhatsApp: +977 9743488871</p>
                                            <p style="margin: 0; font-size: 11px; color: #444;">© 2025 GameShop Nepal. All rights reserved.</p>
                                        </td>
                                    </tr>
                                    
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
                text = f"Order #{order_number} Complete!\n\nYour order has been completed.\n{'You earned Rs ' + str(int(credits_awarded)) + ' in store credits!' if credits_awarded > 0 else ''}\nView Invoice: {invoice_url}\nLeave a Review: {review_url}"
                
                send_email(customer_email, subject, html, text)
                logger.info(f"Invoice email sent to {customer_email} for completed order {order_id}")
            except Exception as e:
                logger.error(f"Failed to send invoice email for completed order {order_id}: {e}")
        
        # Return early - don't send the generic status update email for completed orders
        response = {"message": f"Order status updated to {status_data.status}"}
        if credits_awarded > 0:
            response["credits_awarded"] = credits_awarded
        return response
    
    # Send status update email
    if customer_email:
        try:
            subject, html, text = get_order_status_update_email(order, status_data.status)
            send_email(customer_email, subject, html, text)
            logger.info(f"Order status update email sent to {customer_email}")
        except Exception as e:
            logger.error(f"Failed to send status update email: {e}")
    
    response = {"message": f"Order status updated to {status_data.status}"}
    if credits_deducted > 0:
        response["credits_deducted"] = credits_deducted
    if credits_awarded > 0:
        response["credits_awarded"] = credits_awarded
    return response

@router.get("/orders/{order_id}")
async def get_order_details(order_id: str, current_user: dict = Depends(get_current_user)):
    """Admin: Get full order details"""
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    history = await db.order_status_history.find(
        {"order_id": order_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    
    order["status_history"] = history
    return order

