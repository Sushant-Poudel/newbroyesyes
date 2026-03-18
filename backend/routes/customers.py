"""Customer authentication, profiles, and management routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import db, JWT_SECRET, JWT_ALGORITHM, GOOGLE_CLIENT_ID, TAKEAPP_API_KEY, TAKEAPP_BASE_URL
from dependencies import get_current_user, get_current_customer, check_permission, create_audit_log, create_token
import uuid
import os
import logging
import jwt
import httpx
import asyncio
import secrets
from email_service import send_email, get_welcome_email

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== MODELS ====================

class OTPRequest(BaseModel):
    email: str
    name: Optional[str] = None
    whatsapp_number: str

class OTPVerify(BaseModel):
    email: str
    otp: str

class CustomerLogin(BaseModel):
    email: str
    otp: Optional[str] = None

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    credential: str

class GoogleProfileCompletion(BaseModel):
    email: str
    phone: str


# ==================== CUSTOMER AUTH ROUTES ====================

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)

@router.post("/auth/customer/send-otp")
async def send_customer_otp(request: OTPRequest):
    """Send OTP to customer email"""
    email = request.email.lower().strip()
    
    # Validate required fields
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    if not request.whatsapp_number or not request.whatsapp_number.strip():
        raise HTTPException(status_code=400, detail="WhatsApp number is required")
    
    # Check if customer exists, if not create profile
    customer = await db.customers.find_one({"email": email})
    if not customer:
        customer_data = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": request.name or email.split("@")[0],
            "phone": request.whatsapp_number,
            "whatsapp_number": request.whatsapp_number,
            "credit_balance": 0.0,  # Initialize credit balance
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None
        }
        await db.customers.insert_one(customer_data)
        logger.info(f"New customer created: {email}")
    else:
        # Update whatsapp_number if provided
        if request.whatsapp_number:
            await db.customers.update_one(
                {"email": email},
                {"$set": {"whatsapp_number": request.whatsapp_number, "phone": request.whatsapp_number}}
            )
    
    # Generate OTP
    otp = generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    
    # Store OTP
    otp_record = OTPRecord(
        email=email,
        otp=otp,
        expires_at=expires_at
    )
    
    # Delete old OTPs for this email
    await db.otp_records.delete_many({"email": email})
    await db.otp_records.insert_one(otp_record.model_dump())
    
    # Send OTP via email
    try:
        subject = f"Your GSN Login Code: {otp}"
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #000000; color: #ffffff;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
                    <h1 style="margin: 0; color: #F5A623; font-size: 32px; font-weight: bold;">GSN</h1>
                    <p style="margin: 10px 0 0; color: #888;">GameShop Nepal</p>
                </div>
                
                <div style="padding: 40px 0; text-align: center;">
                    <h2 style="color: #F5A623; margin: 0 0 20px;">Your Login Code</h2>
                    <p style="color: #cccccc; margin-bottom: 30px;">Use this code to log in to your account:</p>
                    
                    <div style="background: linear-gradient(145deg, #1a1a1a, #0a0a0a); border: 2px solid #F5A623; border-radius: 12px; padding: 30px; margin: 20px 0;">
                        <div style="font-size: 48px; font-weight: bold; color: #F5A623; letter-spacing: 8px; font-family: monospace;">
                            {otp}
                        </div>
                    </div>
                    
                    <p style="color: #888; font-size: 14px; margin-top: 30px;">
                        This code expires in 10 minutes.
                    </p>
                    <p style="color: #666; font-size: 12px; margin-top: 10px;">
                        If you didn't request this code, please ignore this email.
                    </p>
                </div>
                
                <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a;">
                    <p style="color: #888; margin: 5px 0;">Questions? Contact us on WhatsApp</p>
                    <p style="color: #888; margin: 5px 0;">+977 9743488871</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text = f"""
        GSN - GAMESHOP NEPAL
        
        Your Login Code: {otp}
        
        This code expires in 10 minutes.
        
        If you didn't request this code, please ignore this email.
        
        Questions? WhatsApp: +977 9743488871
        """
        
        send_email(email, subject, html, text)
        logger.info(f"OTP sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
    
    # Return OTP in response if debug mode enabled (for testing without email)
    if os.environ.get("DEBUG_MODE") == "true":
        return {"message": "OTP sent (debug mode)", "otp": otp, "expires_in": "10 minutes"}
    
    return {"message": "OTP sent to your email", "expires_in": "10 minutes"}


async def send_customer_welcome_email(customer: dict, is_new: bool = False):
    """Send welcome/login notification email with profile details"""
    email = customer.get("email")
    if not email:
        return
    try:
        name = customer.get("name") or "Customer"
        phone = customer.get("phone") or customer.get("whatsapp_number") or "Not set"
        registered = customer.get("created_at", "")[:10] or "N/A"
        site_url = os.environ.get("SITE_URL", "https://gameshopnepal.com")
        account_url = f"{site_url}/account"

        subject = "Welcome to GameShop Nepal!" if is_new else "Login Notification - GameShop Nepal"
        greeting = "Welcome aboard!" if is_new else "You just logged in."

        html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:520px;margin:0 auto;background:#111;border:1px solid #222;border-radius:12px;overflow:hidden;">
          <div style="background:linear-gradient(135deg,#d97706,#b45309);padding:28px 24px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:22px;">GameShop Nepal</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:13px;">{greeting}</p>
          </div>
          <div style="padding:24px;">
            <p style="color:#ccc;font-size:14px;margin:0 0 18px;">Hi <strong style="color:#fff;">{name}</strong>, here are your profile details:</p>
            <table style="width:100%;border-collapse:collapse;">
              <tr><td style="padding:10px 12px;color:#999;font-size:13px;border-bottom:1px solid #222;">Name</td><td style="padding:10px 12px;color:#fff;font-size:13px;border-bottom:1px solid #222;text-align:right;">{name}</td></tr>
              <tr><td style="padding:10px 12px;color:#999;font-size:13px;border-bottom:1px solid #222;">Email</td><td style="padding:10px 12px;color:#fff;font-size:13px;border-bottom:1px solid #222;text-align:right;">{email}</td></tr>
              <tr><td style="padding:10px 12px;color:#999;font-size:13px;border-bottom:1px solid #222;">Phone</td><td style="padding:10px 12px;color:#fff;font-size:13px;border-bottom:1px solid #222;text-align:right;">{phone}</td></tr>
              <tr><td style="padding:10px 12px;color:#999;font-size:13px;">Registered</td><td style="padding:10px 12px;color:#fff;font-size:13px;text-align:right;">{registered}</td></tr>
            </table>
            <div style="text-align:center;margin:24px 0 8px;">
              <a href="{account_url}" style="display:inline-block;background:#d97706;color:#000;font-weight:600;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;">View My Account</a>
            </div>
          </div>
          <div style="padding:16px 24px;border-top:1px solid #222;text-align:center;">
            <p style="margin:0;color:#666;font-size:11px;">If this wasn't you, please ignore this email or contact support.</p>
          </div>
        </div>
        """
        send_email(to_email=email, subject=subject, html_body=html)
    except Exception as e:
        logger.warning(f"Failed to send welcome email to {email}: {e}")


@router.post("/auth/customer/verify-otp")
async def verify_customer_otp(verify: OTPVerify):
    """Verify OTP and create customer session"""
    email = verify.email.lower().strip()
    
    # Find OTP record
    otp_record = await db.otp_records.find_one({
        "email": email,
        "otp": verify.otp,
        "verified": False
    })
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Check expiry
    expires_at = datetime.fromisoformat(otp_record["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")
    
    # Mark OTP as verified
    await db.otp_records.update_one(
        {"id": otp_record["id"]},
        {"$set": {"verified": True}}
    )
    
    # Update customer last login
    await db.customers.update_one(
        {"email": email},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get customer profile
    customer = await db.customers.find_one({"email": email}, {"_id": 0})
    
    # If customer doesn't exist somehow, create it
    if not customer:
        customer = {
            "id": str(uuid.uuid4()),
            "email": email,
            "name": email.split("@")[0],
            "phone": None,
            "credit_balance": 0.0,  # Initialize credit balance
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat()
        }
        await db.customers.insert_one(customer)
    
    # Sync customer to Google Sheets (in background)
    try:
        google_sheets_service.sync_customer_to_sheets(customer)
    except Exception as e:
        logger.warning(f"Failed to sync customer to Google Sheets: {e}")
    
    # Create JWT token for customer
    token = create_token(customer["id"])
    
    # Send login notification email
    is_new = customer.get("created_at", "") == customer.get("last_login", "")
    asyncio.create_task(send_customer_welcome_email(customer, is_new=is_new))
    
    return {
        "token": token,
        "customer": customer,
        "message": "Login successful"
    }

@router.get("/auth/customer/me")
async def get_customer_profile(current_customer: dict = Depends(get_current_customer)):
    """Get current customer profile"""
    return current_customer


# ==================== GOOGLE OAUTH ====================


# ==================== CUSTOMER ENDPOINTS ====================

@router.get("/customer/orders")
async def get_customer_orders(current_customer: dict = Depends(get_current_customer)):
    """Get customer's order history with status history"""
    orders = await db.orders.find(
        {"customer_email": current_customer["email"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Batch fetch all status histories to avoid N+1 query
    order_ids = [order.get("id") for order in orders if order.get("id")]
    if order_ids:
        all_histories = await db.order_status_history.find(
            {"order_id": {"$in": order_ids}},
            {"_id": 0}
        ).sort("created_at", 1).to_list(5000)
        
        # Group histories by order_id
        history_map = {}
        for h in all_histories:
            oid = h.get("order_id")
            if oid not in history_map:
                history_map[oid] = []
            history_map[oid].append(h)
        
        # Assign histories to orders
        for order in orders:
            order["status_history"] = history_map.get(order.get("id"), [])
    else:
        for order in orders:
            order["status_history"] = []
    
    return orders

@router.get("/customer/orders/{order_id}")
async def get_customer_order_detail(order_id: str, current_customer: dict = Depends(get_current_customer)):
    """Get specific order details"""
    order = await db.orders.find_one({
        "id": order_id,
        "customer_email": current_customer["email"]
    }, {"_id": 0})
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get status history
    history = await db.order_status_history.find(
        {"order_id": order_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(50)
    
    order["status_history"] = history
    return order

@router.get("/customer/stats")
async def get_customer_stats(current_customer: dict = Depends(get_current_customer)):
    """Get customer statistics"""
    email = current_customer["email"]
    
    # Count orders
    total_orders = await db.orders.count_documents({"customer_email": email})
    
    # Calculate total spent with projection (only fetch total_amount)
    orders = await db.orders.find(
        {"customer_email": email}, 
        {"total_amount": 1, "_id": 0}
    ).to_list(1000)
    total_spent = sum(order.get("total_amount", 0) for order in orders)
    
    # Count wishlist items
    wishlist_count = await db.wishlists.count_documents({"email": email})
    
    return {
        "total_orders": total_orders,
        "total_spent": total_spent,
        "wishlist_items": wishlist_count,
        "member_since": current_customer.get("created_at", "")[:10]
    }


@router.put("/auth/customer/profile")
async def update_customer_profile(name: str, phone: Optional[str] = None, current_customer: dict = Depends(get_current_customer)):
    """Update customer profile"""
    await db.customers.update_one(
        {"id": current_customer["id"]},
        {"$set": {"name": name, "phone": phone}}
    )
    
    updated = await db.customers.find_one({"id": current_customer["id"]}, {"_id": 0})
    return updated



# ==================== CUSTOMER ACCOUNTS ====================

class CustomerLogin(BaseModel):
    phone: str
    otp: Optional[str] = None

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    
@router.post("/customers/login")
async def customer_login(data: CustomerLogin):
    """Login/Register customer by phone number - sends OTP or validates"""
    phone = data.phone.strip().replace(" ", "").replace("-", "")
    
    # Find or create customer
    customer = await db.customers.find_one({"phone": phone})
    
    if not data.otp:
        # Generate OTP (in production, send via SMS)
        import random
        otp = str(random.randint(100000, 999999))
        
        if customer:
            await db.customers.update_one({"phone": phone}, {"$set": {"otp": otp, "otp_expires": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}})
        else:
            await db.customers.insert_one({
                "id": str(uuid.uuid4()),
                "phone": phone,
                "name": None,
                "email": None,
                "otp": otp,
                "otp_expires": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "total_orders": 0,
                "total_spent": 0
            })
        
        # In production, send OTP via SMS. For now, return it (dev mode)
        return {"message": "OTP sent", "dev_otp": otp}  # Remove dev_otp in production
    
    else:
        # Validate OTP
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        if customer.get("otp") != data.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        if customer.get("otp_expires") and customer["otp_expires"] < datetime.now(timezone.utc).isoformat():
            raise HTTPException(status_code=400, detail="OTP expired")
        
        # Clear OTP and generate token
        await db.customers.update_one({"phone": phone}, {"$unset": {"otp": "", "otp_expires": ""}})
        
        token = jwt.encode(
            {"customer_id": customer["id"], "phone": phone, "exp": datetime.now(timezone.utc) + timedelta(days=30)},
            JWT_SECRET,
            algorithm="HS256"
        )
        
        # Send login email if customer has email
        if customer.get("email"):
            asyncio.create_task(send_customer_welcome_email(customer, is_new=False))
        
        return {
            "token": token,
            "customer": {
                "id": customer["id"],
                "phone": customer["phone"],
                "name": customer.get("name"),
                "email": customer.get("email")
            }
        }

# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
class GoogleAuthRequest(BaseModel):
    credential: str  # The ID token from Google

class GoogleProfileCompletion(BaseModel):
    name: str
    whatsapp_number: str

@router.post("/customers/google-auth")
async def customer_google_auth(data: GoogleAuthRequest):
    """Authenticate customer via Google Sign-In"""
    try:
        # Verify the Google ID token
        async with httpx.AsyncClient() as client:
            # Verify token with Google
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={data.credential}"
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Invalid Google token")
            
            google_data = response.json()
            
            # Verify the token is for our app
            if google_data.get("aud") != GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Token not issued for this app")
            
            email = google_data.get("email")
            name = google_data.get("name")
            google_id = google_data.get("sub")
            picture = google_data.get("picture")
            
            if not email:
                raise HTTPException(status_code=400, detail="Email not provided by Google")
            
            # Find existing customer by email or google_id
            customer = await db.customers.find_one({
                "$or": [
                    {"email": email},
                    {"google_id": google_id}
                ]
            })
            
            needs_profile_completion = False
            
            if customer:
                # Update existing customer with Google info
                await db.customers.update_one(
                    {"id": customer["id"]},
                    {"$set": {
                        "google_id": google_id,
                        "name": customer.get("name") or name,
                        "email": email,
                        "picture": picture,
                        "last_login": datetime.now(timezone.utc).isoformat()
                    }}
                )
                # Check if profile is complete (has name and whatsapp)
                if not customer.get("whatsapp_number") or not customer.get("name"):
                    needs_profile_completion = True
            else:
                # Create new customer
                needs_profile_completion = True  # New customers always need to complete profile
                customer = {
                    "id": str(uuid.uuid4()),
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "phone": None,
                    "whatsapp_number": None,
                    "picture": picture,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "last_login": datetime.now(timezone.utc).isoformat(),
                    "total_orders": 0,
                    "total_spent": 0,
                    "store_credits": 0
                }
                await db.customers.insert_one(customer)
            
            # Generate JWT token
            token = jwt.encode(
                {
                    "customer_id": customer["id"],
                    "email": email,
                    "exp": datetime.now(timezone.utc) + timedelta(days=30)
                },
                JWT_SECRET,
                algorithm="HS256"
            )
            
            # Send welcome/login email
            customer_for_email = await db.customers.find_one({"id": customer["id"]}, {"_id": 0})
            asyncio.create_task(send_customer_welcome_email(customer_for_email, is_new=needs_profile_completion))

            return {
                "token": token,
                "customer": {
                    "id": customer["id"],
                    "email": email,
                    "name": customer.get("name") or name,
                    "phone": customer.get("phone"),
                    "whatsapp_number": customer.get("whatsapp_number"),
                    "picture": picture
                },
                "needs_profile_completion": needs_profile_completion
            }
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify Google token: {str(e)}")

@router.put("/customers/complete-profile")
async def complete_customer_profile(data: GoogleProfileCompletion, request: Request):
    """Complete customer profile after Google login - requires name and WhatsApp number"""
    # Get token from header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        customer_id = payload.get("customer_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not customer_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Validate input
    if not data.name or not data.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not data.whatsapp_number or not data.whatsapp_number.strip():
        raise HTTPException(status_code=400, detail="WhatsApp number is required")
    
    # Clean WhatsApp number
    whatsapp_clean = data.whatsapp_number.strip().replace(" ", "").replace("-", "")
    
    # Update customer profile
    result = await db.customers.update_one(
        {"id": customer_id},
        {"$set": {
            "name": data.name.strip(),
            "whatsapp_number": whatsapp_clean,
            "phone": whatsapp_clean,  # Also set as phone
            "profile_completed": True
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Fetch updated customer
    customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    
    return {
        "success": True,
        "customer": {
            "id": customer["id"],
            "email": customer.get("email"),
            "name": customer.get("name"),
            "phone": customer.get("phone"),
            "whatsapp_number": customer.get("whatsapp_number"),
            "picture": customer.get("picture")
        }
    }

@router.post("/customers/sync-from-takeapp")
async def sync_customers_from_takeapp(current_user: dict = Depends(get_current_user)):
    """Admin: Sync customer data from Take.app orders"""
    if not TAKEAPP_API_KEY:
        raise HTTPException(status_code=400, detail="Take.app API key not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{TAKEAPP_BASE_URL}/orders?api_key={TAKEAPP_API_KEY}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch Take.app orders")
        
        orders = response.json()
        synced_count = 0
        
        for order in orders:
            phone = order.get("customer_phone") or order.get("phone")
            if not phone:
                continue
            
            phone = phone.strip().replace(" ", "").replace("-", "")
            
            # Find or create customer
            existing = await db.customers.find_one({"phone": phone})
            
            order_amount = float(order.get("total", 0) or 0)
            
            if existing:
                # Update stats
                await db.customers.update_one(
                    {"phone": phone},
                    {
                        "$inc": {"total_orders": 1, "total_spent": order_amount},
                        "$set": {
                            "name": order.get("customer_name") or existing.get("name"),
                            "email": order.get("customer_email") or existing.get("email"),
                            "last_order_at": order.get("created_at") or datetime.now(timezone.utc).isoformat()
                        }
                    }
                )
            else:
                # Create new customer
                await db.customers.insert_one({
                    "id": str(uuid.uuid4()),
                    "phone": phone,
                    "name": order.get("customer_name"),
                    "email": order.get("customer_email"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "total_orders": 1,
                    "total_spent": order_amount,
                    "last_order_at": order.get("created_at"),
                    "source": "takeapp"
                })
                synced_count += 1
        
        return {"message": f"Synced {synced_count} new customers from Take.app", "total_orders_processed": len(orders)}

@router.get("/customers")
async def get_all_customers(current_user: dict = Depends(get_current_user)):
    """Admin: Get all customers with order stats"""
    customers = await db.customers.find({}, {"_id": 0, "otp": 0, "otp_expires": 0}).sort("created_at", -1).to_list(1000)
    
    # Get order stats for all customers
    order_stats = await db.orders.aggregate([
        {"$group": {
            "_id": "$customer_email",
            "total_orders": {"$sum": 1},
            "total_spent": {"$sum": "$total_amount"},
            "phone": {"$first": "$customer_phone"}
        }}
    ]).to_list(10000)
    
    # Create lookup by email
    stats_by_email = {stat["_id"]: stat for stat in order_stats if stat["_id"]}
    
    # Also aggregate by phone for customers without email
    phone_stats = await db.orders.aggregate([
        {"$group": {
            "_id": "$customer_phone",
            "total_orders": {"$sum": 1},
            "total_spent": {"$sum": "$total_amount"}
        }}
    ]).to_list(10000)
    
    stats_by_phone = {stat["_id"]: stat for stat in phone_stats if stat["_id"]}
    
    # Merge order stats into customers
    for customer in customers:
        email = customer.get("email")
        phone = customer.get("phone") or customer.get("whatsapp_number")
        
        # Try to find stats by email first, then by phone
        stats = stats_by_email.get(email) or stats_by_phone.get(phone) or {}
        
        customer["total_orders"] = stats.get("total_orders", 0)
        customer["total_spent"] = stats.get("total_spent", 0)
        
        # If customer doesn't have phone, try to get it from orders
        if not customer.get("phone") and stats.get("phone"):
            customer["phone"] = stats.get("phone")
    
    return customers

