"""Reviews, Trustpilot sync, and FAQ routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import db
from dependencies import get_current_user, get_current_customer
import uuid
import os
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

TRUSTPILOT_DOMAIN = "gameshopnepal.com"
TRUSTPILOT_API_KEY = os.environ.get("TRUSTPILOT_API_KEY", "")


class ReviewCreate(BaseModel):
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    comment: str
    review_date: Optional[str] = None

class CustomerReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reviewer_name: str
    rating: int
    comment: str
    review_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: Optional[str] = None
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    is_customer_review: bool = False
    status: str = "approved"
    order_id: Optional[str] = None

class FAQItemCreate(BaseModel):
    question: str
    answer: str
    category: str = "General"
    sort_order: int = 0

class FAQItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    category: str = "General"
    sort_order: int = 0


# ==================== REVIEWS ====================

@router.get("/reviews")
async def get_reviews():
    reviews = await db.reviews.find({"status": {"$in": ["approved", None]}}, {"_id": 0}).sort("review_date", -1).to_list(20)
    for review in reviews:
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()
        if "review_date" in review and isinstance(review["review_date"], datetime):
            review["review_date"] = review["review_date"].isoformat()
    return reviews

@router.get("/reviews/public")
async def get_reviews_public(page: int = 1, limit: int = 20):
    skip = (page - 1) * limit
    total = await db.reviews.count_documents({"status": {"$in": ["approved", None]}})
    reviews = await db.reviews.find({"status": {"$in": ["approved", None]}}, {"_id": 0}).sort("review_date", -1).skip(skip).limit(limit).to_list(limit)
    for review in reviews:
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()
        if "review_date" in review and isinstance(review["review_date"], datetime):
            review["review_date"] = review["review_date"].isoformat()
    pipeline = [
        {"$match": {"status": {"$in": ["approved", None]}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    stats_result = await db.reviews.aggregate(pipeline).to_list(1)
    avg_rating = round(stats_result[0]["avg_rating"], 1) if stats_result else 0
    dist_pipeline = [
        {"$match": {"status": {"$in": ["approved", None]}}},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    dist_result = await db.reviews.aggregate(dist_pipeline).to_list(5)
    distribution = {str(i): 0 for i in range(1, 6)}
    for d in dist_result:
        distribution[str(d["_id"])] = d["count"]
    return {
        "reviews": reviews, "total": total, "page": page,
        "pages": (total + limit - 1) // limit if limit > 0 else 1,
        "avg_rating": avg_rating, "distribution": distribution
    }

@router.get("/reviews/admin")
async def get_reviews_admin(current_user: dict = Depends(get_current_user)):
    reviews = await db.reviews.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    for review in reviews:
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()
        if "review_date" in review and isinstance(review["review_date"], datetime):
            review["review_date"] = review["review_date"].isoformat()
    return reviews

@router.post("/reviews", response_model=Review)
async def create_review(review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    review = Review(
        reviewer_name=review_data.reviewer_name, rating=review_data.rating,
        comment=review_data.comment,
        review_date=review_data.review_date or datetime.now(timezone.utc).isoformat(),
        status="approved"
    )
    await db.reviews.insert_one(review.model_dump())
    return review

@router.post("/reviews/customer")
async def create_customer_review(review_data: CustomerReviewCreate, current_customer: dict = Depends(get_current_customer)):
    completed_order = await db.orders.find_one({
        "customer_email": current_customer["email"],
        "status": {"$regex": "^(completed|delivered|confirmed)$", "$options": "i"}
    })
    if not completed_order:
        raise HTTPException(status_code=403, detail="You need at least one completed order to leave a review")
    existing_review = await db.reviews.find_one({"customer_id": current_customer["id"], "is_customer_review": True})
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already submitted a review. You can edit it instead.")
    customer_name = current_customer.get("name", current_customer.get("email", "Customer"))
    review = Review(
        reviewer_name=customer_name, rating=review_data.rating, comment=review_data.comment,
        review_date=datetime.now(timezone.utc).isoformat(),
        customer_id=current_customer["id"], customer_email=current_customer["email"],
        is_customer_review=True, status="pending", order_id=completed_order.get("id")
    )
    await db.reviews.insert_one(review.model_dump())
    return {"message": "Review submitted successfully! It will appear after admin approval.", "review_id": review.id}

@router.put("/reviews/customer")
async def update_customer_review(review_data: CustomerReviewCreate, current_customer: dict = Depends(get_current_customer)):
    existing = await db.reviews.find_one({"customer_id": current_customer["id"], "is_customer_review": True})
    if not existing:
        raise HTTPException(status_code=404, detail="You haven't submitted a review yet")
    await db.reviews.update_one(
        {"customer_id": current_customer["id"], "is_customer_review": True},
        {"$set": {"rating": review_data.rating, "comment": review_data.comment, "status": "pending", "review_date": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Review updated! It will appear after admin re-approval."}

@router.get("/reviews/my-review")
async def get_my_review(current_customer: dict = Depends(get_current_customer)):
    review = await db.reviews.find_one({"customer_id": current_customer["id"], "is_customer_review": True}, {"_id": 0})
    has_completed_order = await db.orders.count_documents({
        "customer_email": current_customer["email"],
        "status": {"$regex": "^(completed|delivered|confirmed)$", "$options": "i"}
    }) > 0
    return {"review": review, "can_review": has_completed_order}

@router.put("/reviews/{review_id}/status")
async def update_review_status(review_id: str, status: str, current_user: dict = Depends(get_current_user)):
    if status not in ["approved", "rejected", "pending"]:
        raise HTTPException(status_code=400, detail="Status must be approved, rejected, or pending")
    review = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.reviews.update_one({"id": review_id}, {"$set": {"status": status}})
    promo_code = None
    if status == "approved" and review.get("is_customer_review") and review.get("customer_email"):
        if not review.get("reward_promo_code"):
            reward_settings = await db.site_settings.find_one({"id": "review_reward"}, {"_id": 0})
            reward_pct = 5
            reward_enabled = True
            if reward_settings:
                reward_pct = reward_settings.get("review_reward_percentage", 5)
                reward_enabled = reward_settings.get("review_reward_enabled", True)
            if reward_enabled and reward_pct > 0:
                code_str = f"REVIEW-{review_id[:8].upper()}"
                existing_code = await db.promo_codes.find_one({"code": code_str})
                if existing_code:
                    code_str = f"REVIEW-{uuid.uuid4().hex[:8].upper()}"
                expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                promo = {
                    "id": str(uuid.uuid4()), "code": code_str, "discount_type": "percentage",
                    "discount_value": reward_pct, "min_order_amount": 0, "max_uses": 1,
                    "max_uses_per_customer": 1, "used_count": 0, "is_active": True,
                    "expiry_date": expiry, "applicable_categories": [], "applicable_products": [],
                    "first_time_only": False, "buy_quantity": None, "get_quantity": None,
                    "auto_apply": False, "stackable": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "review_reward", "customer_email": review["customer_email"]
                }
                await db.promo_codes.insert_one(promo)
                await db.reviews.update_one({"id": review_id}, {"$set": {"reward_promo_code": code_str}})
                promo_code = code_str
                try:
                    customer_name = review.get("reviewer_name", "Customer")
                    subject = f"Thank you for your review! Here's {reward_pct}% off - GameShop Nepal"
                    html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #1a1a1a; color: #fff;">
                        <div style="background: linear-gradient(135deg, #F5A623 0%, #D4920D 100%); padding: 30px; text-align: center;">
                            <h1 style="margin: 0; color: #000; font-size: 28px;">Thank You!</h1>
                        </div>
                        <div style="padding: 30px;">
                            <p style="color: #ccc; font-size: 16px;">Hi {customer_name},</p>
                            <p style="color: #ccc; font-size: 16px;">Thank you for sharing your experience! As a token of appreciation, here's a special discount for your next purchase:</p>
                            <div style="background: linear-gradient(135deg, #F5A623 0%, #D4920D 100%); border-radius: 10px; padding: 25px; margin: 25px 0; text-align: center;">
                                <p style="color: #000; margin: 0 0 8px 0; font-size: 14px; font-weight: 600;">YOUR PROMO CODE</p>
                                <p style="color: #000; margin: 0; font-size: 32px; font-weight: 800; letter-spacing: 3px;">{code_str}</p>
                                <p style="color: rgba(0,0,0,0.7); margin: 10px 0 0 0; font-size: 14px;">{reward_pct}% off your next order &bull; Valid for 30 days</p>
                            </div>
                        </div>
                    </div>
                    """
                    text = f"Hi {customer_name}, thank you for your review! Use code {code_str} for {reward_pct}% off your next order. Valid for 30 days."
                    from email_service import send_email
                    send_email(review["customer_email"], subject, html, text)
                except Exception as e:
                    logger.warning(f"Failed to send review reward email: {e}")
    response = {"message": f"Review {status}"}
    if promo_code:
        response["promo_code"] = promo_code
    return response

@router.get("/reviews/reward-settings")
async def get_review_reward_settings(current_user: dict = Depends(get_current_user)):
    settings = await db.site_settings.find_one({"id": "review_reward"}, {"_id": 0})
    if not settings:
        settings = {"id": "review_reward", "review_reward_percentage": 5, "review_reward_enabled": True}
    return settings

@router.put("/reviews/reward-settings")
async def update_review_reward_settings(data: dict, current_user: dict = Depends(get_current_user)):
    data["id"] = "review_reward"
    await db.site_settings.update_one({"id": "review_reward"}, {"$set": data}, upsert=True)
    return data

# NOTE: Trustpilot config routes MUST be defined BEFORE {review_id} routes to avoid path conflicts
@router.get("/reviews/trustpilot-config")
async def get_trustpilot_config(current_user: dict = Depends(get_current_user)):
    """Get Trustpilot configuration."""
    domain = await get_trustpilot_domain()
    last_sync = await db.trustpilot_config.find_one({"key": "last_sync"})
    tp_review_count = await db.reviews.count_documents({"source": "trustpilot"})
    return {
        "domain": domain,
        "last_sync": last_sync.get("value") if last_sync else None,
        "trustpilot_reviews_count": tp_review_count,
    }

@router.put("/reviews/trustpilot-config")
async def update_trustpilot_config(data: dict, current_user: dict = Depends(get_current_user)):
    """Update Trustpilot domain configuration."""
    domain = data.get("domain", "").strip()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain is required")
    await db.trustpilot_config.update_one(
        {"key": "domain"}, {"$set": {"key": "domain", "value": domain}}, upsert=True
    )
    return {"message": "Trustpilot domain updated", "domain": domain}

@router.get("/reviews/trustpilot-reviews")
async def get_trustpilot_reviews(current_user: dict = Depends(get_current_user)):
    """Get all synced Trustpilot reviews."""
    reviews = await db.reviews.find({"source": "trustpilot"}, {"_id": 0}).sort("review_date", -1).to_list(200)
    for review in reviews:
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()
        if "review_date" in review and isinstance(review["review_date"], datetime):
            review["review_date"] = review["review_date"].isoformat()
    return reviews

@router.delete("/reviews/trustpilot-reviews")
async def delete_all_trustpilot_reviews(current_user: dict = Depends(get_current_user)):
    """Delete all synced Trustpilot reviews."""
    result = await db.reviews.delete_many({"source": "trustpilot"})
    await db.trustpilot_config.delete_one({"key": "last_sync"})
    return {"message": f"Deleted {result.deleted_count} Trustpilot reviews"}

@router.put("/reviews/{review_id}")
async def update_review(review_id: str, review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")
    update_data = review_data.model_dump()
    update_data["review_date"] = review_data.review_date or existing.get("review_date")
    await db.reviews.update_one({"id": review_id}, {"$set": update_data})
    updated = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    return updated

@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.reviews.delete_one({"id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted"}


# ==================== TRUSTPILOT SYNC ====================

async def get_trustpilot_domain():
    """Get the configured Trustpilot domain from DB or fallback to env."""
    config = await db.trustpilot_config.find_one({"key": "domain"})
    if config and config.get("value"):
        return config["value"]
    return TRUSTPILOT_DOMAIN

async def fetch_trustpilot_reviews_from_page(domain: str):
    """Scrape reviews from Trustpilot page using JSON-LD and __NEXT_DATA__."""
    import re
    import json as json_mod
    reviews = []
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://www.trustpilot.com/review/{domain}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                timeout=20.0,
                follow_redirects=True
            )
            if response.status_code != 200:
                logger.warning(f"Trustpilot returned status {response.status_code} for {domain}")
                return reviews

            html = response.text

            # Method 1: JSON-LD structured data
            json_ld_pattern = r'<script type="application/ld\+json"[^>]*>(.*?)</script>'
            matches = re.findall(json_ld_pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json_mod.loads(match)
                    if isinstance(data, dict) and data.get("@type") == "LocalBusiness":
                        if "review" in data:
                            for r in data["review"]:
                                reviews.append({
                                    "reviewer_name": r.get("author", {}).get("name", "Anonymous"),
                                    "rating": int(r.get("reviewRating", {}).get("ratingValue", 5)),
                                    "comment": r.get("reviewBody", ""),
                                    "review_date": r.get("datePublished", datetime.now(timezone.utc).isoformat())
                                })
                except json_mod.JSONDecodeError:
                    continue

            # Method 2: __NEXT_DATA__ (React SSR payload)
            next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
            next_matches = re.findall(next_data_pattern, html, re.DOTALL)
            seen = {(r["reviewer_name"], r["comment"]) for r in reviews}
            for match in next_matches:
                try:
                    data = json_mod.loads(match)
                    props = data.get("props", {}).get("pageProps", {})
                    review_list = props.get("reviews", [])
                    for r in review_list:
                        consumer = r.get("consumer", {})
                        dates = r.get("dates", {})
                        published_date = dates.get("publishedDate") or dates.get("experiencedDate")
                        name = consumer.get("displayName", "Anonymous")
                        comment = r.get("text", r.get("title", ""))
                        if (name, comment) not in seen:
                            reviews.append({
                                "reviewer_name": name,
                                "rating": r.get("rating", 5),
                                "comment": comment,
                                "review_date": published_date or datetime.now(timezone.utc).isoformat()
                            })
                            seen.add((name, comment))
                except json_mod.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"Error scraping Trustpilot: {e}")
    return reviews

@router.post("/reviews/sync-trustpilot")
async def sync_trustpilot_reviews(current_user: dict = Depends(get_current_user)):
    """Sync reviews from Trustpilot to the database."""
    domain = await get_trustpilot_domain()
    synced_count = 0
    try:
        trustpilot_reviews = await fetch_trustpilot_reviews_from_page(domain)
        for tp_review in trustpilot_reviews:
            existing = await db.reviews.find_one({
                "reviewer_name": tp_review["reviewer_name"],
                "comment": tp_review["comment"],
                "source": "trustpilot"
            })
            if not existing:
                review = {
                    "id": f"tp-{str(uuid.uuid4())[:8]}",
                    "reviewer_name": tp_review["reviewer_name"],
                    "rating": tp_review["rating"],
                    "comment": tp_review["comment"],
                    "review_date": tp_review["review_date"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "trustpilot",
                    "status": "approved"
                }
                await db.reviews.insert_one(review)
                synced_count += 1
        await db.trustpilot_config.update_one(
            {"key": "last_sync"},
            {"$set": {"key": "last_sync", "value": datetime.now(timezone.utc).isoformat()}}, upsert=True
        )
        return {
            "success": True, "synced_count": synced_count,
            "total_found": len(trustpilot_reviews),
            "message": f"Synced {synced_count} new reviews from Trustpilot"
        }
    except Exception as e:
        logger.error(f"Error syncing Trustpilot reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync reviews: {str(e)}")

@router.get("/reviews/trustpilot-status")
async def get_trustpilot_status(current_user: dict = Depends(get_current_user)):
    """Legacy status endpoint."""
    domain = await get_trustpilot_domain()
    last_sync = await db.trustpilot_config.find_one({"key": "last_sync"})
    tp_review_count = await db.reviews.count_documents({"source": "trustpilot"})
    return {
        "domain": domain, "last_sync": last_sync.get("value") if last_sync else None,
        "trustpilot_reviews_count": tp_review_count, "api_key_configured": bool(TRUSTPILOT_API_KEY)
    }


# ==================== FAQS ====================

@router.get("/faqs", response_model=List[FAQItem])
async def get_faqs():
    faqs = await db.faqs.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return faqs

@router.post("/faqs", response_model=FAQItem)
async def create_faq(faq_data: FAQItemCreate, current_user: dict = Depends(get_current_user)):
    max_order = await db.faqs.find_one(sort=[("sort_order", -1)])
    next_order = (max_order.get("sort_order", 0) + 1) if max_order else 0
    faq = FAQItem(question=faq_data.question, answer=faq_data.answer, sort_order=next_order)
    await db.faqs.insert_one(faq.model_dump())
    return faq

@router.put("/faqs/reorder")
async def reorder_faqs(request: Request, current_user: dict = Depends(get_current_user)):
    faq_ids = await request.json()
    for index, faq_id in enumerate(faq_ids):
        await db.faqs.update_one({"id": faq_id}, {"$set": {"sort_order": index}})
    return {"message": "FAQs reordered successfully"}

@router.put("/faqs/{faq_id}", response_model=FAQItem)
async def update_faq(faq_id: str, faq_data: FAQItemCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.faqs.find_one({"id": faq_id})
    if not existing:
        raise HTTPException(status_code=404, detail="FAQ not found")
    await db.faqs.update_one({"id": faq_id}, {"$set": faq_data.model_dump()})
    updated = await db.faqs.find_one({"id": faq_id}, {"_id": 0})
    return updated

@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.faqs.delete_one({"id": faq_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "FAQ deleted"}
