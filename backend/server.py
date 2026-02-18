from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, Body, Request, Header
import fastapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import string
import random
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import hashlib
import jwt
import secrets
import shutil
import httpx
from email_service import send_email, get_order_confirmation_email, get_order_status_update_email, get_welcome_email
from imgbb_service import upload_to_imgbb
import google_sheets_service
from discord_service import send_discord_order_notification, send_discord_order_status_update
from order_cleanup import run_cleanup_task


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Create uploads directory
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Config
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Take.app Config
TAKEAPP_API_KEY = os.environ.get('TAKEAPP_API_KEY', '')
TAKEAPP_BASE_URL = "https://api.take.app/v1"

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== RATE LIMITING ====================
from collections import defaultdict
from time import time

# In-memory rate limiter (for production, use Redis)
rate_limit_store = defaultdict(list)

def rate_limit_check(ip: str, limit: int = 100, window: int = 60):
    """Check if IP is rate limited. Returns True if allowed, False if limited."""
    now = time()
    # Clean old requests
    rate_limit_store[ip] = [req_time for req_time in rate_limit_store[ip] if now - req_time < window]
    
    if len(rate_limit_store[ip]) >= limit:
        return False
    
    rate_limit_store[ip].append(now)
    return True

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = request.client.host
    
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # More relaxed for login endpoints (30 attempts per minute)
    if "/auth/login" in request.url.path:
        if not rate_limit_check(client_ip, limit=30, window=60):
            return fastapi.responses.JSONResponse(
                status_code=429,
                content={"detail": "Too many login attempts. Please try again later."}
            )
    else:
        # General rate limit
        if not rate_limit_check(client_ip, limit=100, window=60):
            return fastapi.responses.JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."}
            )
    
    return await call_next(request)

# ==================== SECURITY HEADERS ====================
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str = "Admin"

class UserLogin(BaseModel):
    email: str
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    is_admin: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Customer Models
class CustomerProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_login: Optional[str] = None

class OTPRequest(BaseModel):
    email: str
    name: Optional[str] = None
    whatsapp_number: str  # Required for login

class OTPVerify(BaseModel):
    email: str
    otp: str

class OTPRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    otp: str
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified: bool = False


class ProductVariation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    original_price: Optional[float] = None
    cost_price: Optional[float] = None  # Admin only - for profit calculation
    description: Optional[str] = None

class ProductFormField(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    placeholder: str = ""
    required: bool = False

class ProductCreate(BaseModel):
    name: str
    slug: Optional[str] = None  # Custom slug, auto-generated if not provided
    description: str
    image_url: str
    category_id: str
    variations: List[ProductVariation] = []
    tags: List[str] = []
    sort_order: int = 0
    custom_fields: List[ProductFormField] = []
    is_active: bool = True
    is_sold_out: bool = False
    stock_quantity: Optional[int] = None  # None means unlimited
    flash_sale_end: Optional[str] = None  # ISO datetime when flash sale ends
    flash_sale_label: Optional[str] = None  # e.g., "FLASH SALE - 50% OFF"
    whatsapp_only: bool = False  # If True, show WhatsApp button instead of order buttons
    whatsapp_message: Optional[str] = None  # Custom WhatsApp message template
    discord_webhooks: List[str] = []  # Discord webhook URLs for order notifications

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: Optional[str] = None
    description: str
    image_url: str
    category_id: str
    variations: List[ProductVariation] = []
    tags: List[str] = []
    sort_order: int = 0
    custom_fields: List[ProductFormField] = []
    is_active: bool = True
    is_sold_out: bool = False
    stock_quantity: Optional[int] = None  # None means unlimited
    flash_sale_end: Optional[str] = None  # ISO datetime when flash sale ends
    flash_sale_label: Optional[str] = None  # e.g., "FLASH SALE - 50% OFF"
    whatsapp_only: bool = False  # If True, show WhatsApp button instead of order buttons
    whatsapp_message: Optional[str] = None  # Custom WhatsApp message template
    discord_webhooks: List[str] = []  # Discord webhook URLs for order notifications (admin only)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ProductOrderUpdate(BaseModel):
    product_ids: List[str]

class ReviewCreate(BaseModel):
    reviewer_name: str
    rating: int = Field(ge=1, le=5)
    comment: str
    review_date: Optional[str] = None

class Review(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reviewer_name: str
    rating: int
    comment: str
    review_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: Optional[str] = None

class PageContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    page_key: str
    title: str
    content: str
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SocialLinkCreate(BaseModel):
    platform: str
    url: str
    icon: Optional[str] = None

class SocialLink(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str
    url: str
    icon: Optional[str] = None

class CategoryCreate(BaseModel):
    name: str

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str

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

class FAQReorderRequest(BaseModel):
    faq_ids: List[str]

# Promo Code Models
class PromoCodeCreate(BaseModel):
    code: str
    discount_type: str = "percentage"  # "percentage", "fixed", "buy_x_get_y", "free_shipping"
    discount_value: float
    min_order_amount: float = 0
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    is_active: bool = True
    expiry_date: Optional[str] = None
    applicable_categories: List[str] = []  # Empty means all categories
    applicable_products: List[str] = []  # Empty means all products
    first_time_only: bool = False
    buy_quantity: Optional[int] = None  # For "buy X get Y" offers
    get_quantity: Optional[int] = None
    auto_apply: bool = False  # Auto-apply if conditions met
    stackable: bool = False  # Can be combined with other promos

class PromoCode(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    discount_type: str = "percentage"
    discount_value: float
    min_order_amount: float = 0
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    used_count: int = 0
    is_active: bool = True
    expiry_date: Optional[str] = None
    applicable_categories: List[str] = []
    applicable_products: List[str] = []
    first_time_only: bool = False
    buy_quantity: Optional[int] = None
    get_quantity: Optional[int] = None
    auto_apply: bool = False
    stackable: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# Store Credit Models
class CreditSettings(BaseModel):
    cashback_percentage: float = 5.0  # Default 5% cashback
    is_enabled: bool = True
    eligible_categories: List[str] = []  # Empty means all categories
    eligible_products: List[str] = []  # Empty means all products
    min_order_amount: float = 0  # Minimum order to earn credits
    usable_categories: List[str] = []  # Categories where credits can be used (empty = all)
    usable_products: List[str] = []  # Products where credits can be used (empty = all)

class CustomerCreditUpdate(BaseModel):
    customer_id: str
    amount: float  # Positive to add, negative to deduct
    reason: str = "Manual adjustment"

# ==================== HELPERS ====================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ==================== ADMIN CREDENTIALS FROM ENV ====================
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "gsnadmin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "gsnadmin")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        if not user_id:
            logger.error(f"No user_id in token payload: {payload}")
            raise HTTPException(status_code=401, detail="Invalid token: no user_id")
        
        # Check if it's the new admin system (search by id field, not _id)
        admin = await db.admins.find_one({"id": user_id})
        if admin and admin.get("is_active"):
            return {
                "id": admin.get("id"),
                "username": admin.get("username"),
                "email": admin.get("email"),
                "name": admin.get("name"),
                "role": admin.get("role"),
                "permissions": admin.get("permissions", []),
                "is_admin": True,
                "is_main_admin": admin.get("role") == "main_admin" or admin.get("is_main_admin")
            }
        
        # Fallback to old admin system (for backward compatibility)
        if user_id == "admin-fixed" or user_id == "admin_main":
            return {
                "id": user_id,
                "email": ADMIN_USERNAME,
                "name": "Main Admin",
                "is_admin": True,
                "is_main_admin": True,
                "permissions": ["all"]
            }
        
        logger.error(f"User not found for user_id: {user_id}")
        raise HTTPException(status_code=401, detail="Invalid user")
    except jwt.ExpiredSignatureError:
        logger.error("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

def check_permission(user: dict, required_permission: str) -> bool:
    """Check if user has required permission"""
    if user.get("permissions") and "all" in user["permissions"]:
        return True
    return required_permission in user.get("permissions", [])

# ==================== AUTH ROUTES ====================

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    raise HTTPException(status_code=403, detail="Registration disabled. Use admin credentials.")

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    # Try new admin system first
    admin = await db.admins.find_one({"username": credentials.email})
    if admin:
        hashed_password = hash_password(credentials.password)
        if admin["password"] == hashed_password and admin.get("is_active"):
            # Update last login
            await db.admins.update_one(
                {"id": admin["id"]},
                {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
            )
            
            token = create_token(admin["id"])
            return {
                "token": token,
                "user": {
                    "id": admin["id"],
                    "username": admin.get("username"),
                    "email": admin.get("email"),
                    "name": admin.get("name"),
                    "role": admin.get("role"),
                    "permissions": admin.get("permissions", []),
                    "is_admin": True,
                    "is_main_admin": admin.get("role") == "main_admin" or admin.get("is_main_admin")
                }
            }
    
    # Fallback to old admin system - create/update main admin in DB
    if credentials.email == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD:
        # Ensure main admin exists in database
        main_admin_id = "admin_main"
        existing_main = await db.admins.find_one({"id": main_admin_id})
        
        if not existing_main:
            # Create main admin in database
            main_admin_doc = {
                "id": main_admin_id,
                "username": ADMIN_USERNAME,
                "email": f"{ADMIN_USERNAME}@gameshopnepal.com",
                "name": "Main Admin",
                "password": hash_password(ADMIN_PASSWORD),
                "role": "main_admin",
                "is_main_admin": True,
                "is_active": True,
                "permissions": ["all"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.admins.insert_one(main_admin_doc)
            logger.info("Main admin created in database")
        else:
            # Update last login
            await db.admins.update_one(
                {"id": main_admin_id},
                {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
            )
        
        token = create_token(main_admin_id)
        return {
            "token": token,
            "user": {
                "id": main_admin_id,
                "email": ADMIN_USERNAME,
                "name": "Main Admin",
                "is_admin": True,
                "is_main_admin": True,
                "permissions": ["all"]
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user



# ==================== ADMIN MANAGEMENT ROUTES ====================

@api_router.get("/admins")
async def get_all_admins(current_user: dict = Depends(get_current_user)):
    """Get all admins - only main admin can see this"""
    if not current_user.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Only main admin can view all admins")
    
    admins = await db.admins.find({}, {"password": 0}).sort("created_at", -1).to_list(100)
    
    # Normalize response - ensure both id and _id work for frontend compatibility
    result = []
    for admin in admins:
        admin_data = {k: v for k, v in admin.items() if k != "_id"}
        # Ensure id field exists
        if "id" not in admin_data and "_id" in admin:
            admin_data["id"] = str(admin["_id"])
        result.append(admin_data)
    
    return result

@api_router.post("/admins")
async def create_admin(admin_data: dict, current_user: dict = Depends(get_current_user)):
    """Create new staff admin - only main admin can do this"""
    if not current_user.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Only main admin can create staff admins")
    
    # Check if username already exists
    existing = await db.admins.find_one({"username": admin_data["username"]})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    admin_id = f"admin_{admin_data['username']}"
    new_admin = {
        "id": admin_id,
        "username": admin_data["username"],
        "password": hash_password(admin_data["password"]),
        "email": admin_data.get("email", ""),
        "name": admin_data.get("name", admin_data["username"]),
        "role": "staff",
        "is_active": True,
        "permissions": admin_data.get("permissions", ["view_dashboard", "view_orders"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user["id"]
    }
    
    await db.admins.insert_one(new_admin)
    
    # Return without password and _id
    return {
        "message": "Staff admin created successfully", 
        "admin": {
            "id": admin_id,
            "username": new_admin["username"],
            "email": new_admin["email"],
            "name": new_admin["name"],
            "role": new_admin["role"],
            "is_active": new_admin["is_active"],
            "permissions": new_admin["permissions"]
        }
    }

@api_router.put("/admins/{admin_id}")
async def update_admin(admin_id: str, admin_data: dict, current_user: dict = Depends(get_current_user)):
    """Update admin permissions - only main admin can do this"""
    if not current_user.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Only main admin can update admins")
    
    # Log for debugging
    logger.info(f"Updating admin with id: {admin_id}")
    
    # Check if admin exists - try both id and _id fields for backward compatibility
    existing = await db.admins.find_one({"id": admin_id})
    if not existing:
        # Try with _id for old entries
        existing = await db.admins.find_one({"_id": admin_id})
        if existing:
            # Migrate: add id field if missing
            await db.admins.update_one(
                {"_id": admin_id},
                {"$set": {"id": admin_id}}
            )
            logger.info(f"Migrated admin {admin_id} to use id field")
    
    if not existing:
        logger.error(f"Admin not found: {admin_id}")
        raise HTTPException(status_code=404, detail="Admin not found")
    
    update_data = {}
    if "permissions" in admin_data:
        update_data["permissions"] = admin_data["permissions"]
    if "is_active" in admin_data:
        update_data["is_active"] = admin_data["is_active"]
    if "name" in admin_data:
        update_data["name"] = admin_data["name"]
    if "email" in admin_data:
        update_data["email"] = admin_data["email"]
    if "password" in admin_data and admin_data["password"]:
        update_data["password"] = hash_password(admin_data["password"])
    
    # Update using whichever field exists
    if existing.get("id"):
        await db.admins.update_one({"id": admin_id}, {"$set": update_data})
    else:
        await db.admins.update_one({"_id": admin_id}, {"$set": update_data})
    
    return {"message": "Admin updated successfully"}

@api_router.delete("/admins/{admin_id}")
async def delete_admin(admin_id: str, current_user: dict = Depends(get_current_user)):
    """Delete staff admin - only main admin can do this"""
    if not current_user.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Only main admin can delete admins")
    
    # Cannot delete main admin
    if admin_id == "admin_main" or admin_id == "admin-fixed":
        raise HTTPException(status_code=400, detail="Cannot delete main admin")
    
    # Try deleting by id first, then by _id for backward compatibility
    result = await db.admins.delete_one({"id": admin_id})
    if result.deleted_count == 0:
        result = await db.admins.delete_one({"_id": admin_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    return {"message": "Admin deleted successfully"}

@api_router.get("/permissions")
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """Get all available permissions"""
    if not current_user.get("is_main_admin"):
        raise HTTPException(status_code=403, detail="Only main admin can view permissions")
    
    permissions = await db.permissions.find({}, {"_id": 0}).to_list(100)
    
    # If no permissions exist, seed default permissions
    if not permissions:
        default_permissions = [
            # Dashboard
            {"id": "view_dashboard", "name": "View Dashboard", "category": "Dashboard"},
            
            # Orders
            {"id": "view_orders", "name": "View Orders", "category": "Orders"},
            {"id": "manage_orders", "name": "Manage Orders (Update Status)", "category": "Orders"},
            
            # Products
            {"id": "view_products", "name": "View Products", "category": "Products"},
            {"id": "manage_products", "name": "Add/Edit/Delete Products", "category": "Products"},
            
            # Categories
            {"id": "view_categories", "name": "View Categories", "category": "Categories"},
            {"id": "manage_categories", "name": "Add/Edit/Delete Categories", "category": "Categories"},
            
            # Reviews
            {"id": "view_reviews", "name": "View Reviews", "category": "Reviews"},
            {"id": "manage_reviews", "name": "Add/Edit/Delete Reviews", "category": "Reviews"},
            
            # Customers
            {"id": "view_customers", "name": "View Customers", "category": "Customers"},
            {"id": "manage_customers", "name": "Manage Customers", "category": "Customers"},
            
            # Content
            {"id": "manage_blog", "name": "Manage Blog Posts", "category": "Content"},
            {"id": "manage_faqs", "name": "Manage FAQs", "category": "Content"},
            {"id": "manage_pages", "name": "Manage Static Pages", "category": "Content"},
            
            # Settings
            {"id": "manage_payment_methods", "name": "Manage Payment Methods", "category": "Settings"},
            {"id": "manage_promo_codes", "name": "Manage Promo Codes", "category": "Settings"},
            {"id": "manage_social_links", "name": "Manage Social Links", "category": "Settings"},
            {"id": "manage_notification_bar", "name": "Manage Notification Bar", "category": "Settings"},
            
            # Analytics
            {"id": "view_analytics", "name": "View Analytics", "category": "Analytics"},
        ]
        
        # Insert default permissions
        for perm in default_permissions:
            await db.permissions.update_one(
                {"id": perm["id"]},
                {"$set": perm},
                upsert=True
            )
        
        logger.info("Default permissions seeded")
        permissions = default_permissions
    
    return permissions


# ==================== CUSTOMER AUTH ROUTES ====================

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(900000) + 100000)

@api_router.post("/auth/customer/send-otp")
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

@api_router.post("/auth/customer/verify-otp")
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
    
    return {
        "token": token,
        "customer": customer,
        "message": "Login successful"
    }

async def get_current_customer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current logged-in customer"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        # Check if it's a customer by ID
        customer = await db.customers.find_one({"id": user_id}, {"_id": 0})
        if customer:
            return customer
        
        # Fallback: check by customer_id key (for backward compatibility)
        customer_id = payload.get("customer_id")
        if customer_id:
            customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
            if customer:
                return customer
        
        raise HTTPException(status_code=401, detail="Invalid customer token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@api_router.get("/auth/customer/me")
async def get_customer_profile(current_customer: dict = Depends(get_current_customer)):
    """Get current customer profile"""
    return current_customer


# ==================== CUSTOMER ENDPOINTS ====================

@api_router.get("/customer/orders")
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

@api_router.get("/customer/orders/{order_id}")
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

@api_router.get("/customer/stats")
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


@api_router.put("/auth/customer/profile")
async def update_customer_profile(name: str, phone: Optional[str] = None, current_customer: dict = Depends(get_current_customer)):
    """Update customer profile"""
    await db.customers.update_one(
        {"id": current_customer["id"]},
        {"$set": {"name": name, "phone": phone}}
    )
    
    updated = await db.customers.find_one({"id": current_customer["id"]}, {"_id": 0})
    return updated

# ==================== IMAGE UPLOAD ====================

@api_router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WebP, GIF allowed.")

    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOADS_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"/api/uploads/{filename}"}

@api_router.post("/upload/payment")
async def upload_payment_image(file: UploadFile = File(...)):
    """Public endpoint for uploading payment screenshots - using ImgBB"""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WebP, GIF allowed.")
    
    # Limit file size to 10MB
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB allowed.")
    
    try:
        # Generate unique filename
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"payment_{uuid.uuid4()}.{file_ext}"
        
        # Upload to ImgBB
        result = await upload_to_imgbb(
            image_bytes=contents,
            filename=filename
        )
        
        logger.info(f"Payment screenshot uploaded to ImgBB: {filename}")
        
        return {
            "url": result['url'],  # Direct image URL for display
            "image_id": result['image_id'],
            "delete_url": result['delete_url']
        }
    
    except Exception as e:
        logger.error(f"Failed to upload payment screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload screenshot: {str(e)}")

@api_router.get("/uploads/{filename}")
async def get_uploaded_image(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)

# ==================== CATEGORY ROUTES ====================

@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    categories = await db.categories.find({}, {"_id": 0}).to_list(100)
    return categories

@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate, current_user: dict = Depends(get_current_user)):
    slug = category_data.name.lower().replace(" ", "-").replace("&", "and")
    category = Category(name=category_data.name, slug=slug)
    await db.categories.insert_one(category.model_dump())
    return category

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, category_data: CategoryCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.categories.find_one({"id": category_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    slug = category_data.name.lower().replace(" ", "-").replace("&", "and")
    await db.categories.update_one({"id": category_id}, {"$set": {"name": category_data.name, "slug": slug}})
    updated = await db.categories.find_one({"id": category_id}, {"_id": 0})
    return updated

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.categories.delete_one({"id": category_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}

# ==================== PRODUCT ROUTES ====================

@api_router.get("/products", response_model=List[Product])
async def get_products(category_id: Optional[str] = None, active_only: bool = True):
    query = {}
    if category_id:
        query["category_id"] = category_id
    if active_only:
        query["is_active"] = True

    products = await db.products.find(query, {"_id": 0}).sort([("sort_order", 1), ("created_at", -1)]).to_list(1000)
    
    # Convert datetime fields to ISO strings and hide sensitive data
    for product in products:
        if "created_at" in product and isinstance(product["created_at"], datetime):
            product["created_at"] = product["created_at"].isoformat()
        if "updated_at" in product and isinstance(product["updated_at"], datetime):
            product["updated_at"] = product["updated_at"].isoformat()
        # Hide Discord webhooks from public API response (set to empty array for model validation)
        if "discord_webhooks" in product:
            product["discord_webhooks"] = []
    
    return products

@api_router.get("/products/search/advanced")
async def advanced_product_search(
    q: Optional[str] = None,
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    tags: Optional[str] = None,
    sort_by: str = "relevance",  # relevance, price_low, price_high, newest
    limit: int = 50
):
    """Advanced product search with filters"""
    query = {"is_active": True}
    
    # Text search
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}}
        ]
    
    # Category filter
    if category_id:
        query["category_id"] = category_id
    
    # Tags filter
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query["tags"] = {"$in": tag_list}
    
    # Get products
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    
    # Price filter (done in Python since prices are in variations)
    if min_price is not None or max_price is not None:
        filtered = []
        for product in products:
            if product.get("variations"):
                prices = [v["price"] for v in product["variations"]]
                min_p = min(prices)
                max_p = max(prices)
                
                if min_price and max_p < min_price:
                    continue
                if max_price and min_p > max_price:
                    continue
                    
                filtered.append(product)
        products = filtered
    
    # Sorting
    if sort_by == "price_low":
        products.sort(key=lambda p: min([v["price"] for v in p.get("variations", [{"price": 0}])]))
    elif sort_by == "price_high":
        products.sort(key=lambda p: max([v["price"] for v in p.get("variations", [{"price": 0}])]), reverse=True)
    elif sort_by == "newest":
        products.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    
    return products[:limit]

@api_router.get("/products/search/suggestions")
async def search_suggestions(q: str, limit: int = 5):
    """Get search suggestions/autocomplete"""
    if not q or len(q) < 2:
        return []
    
    # Find matching products
    products = await db.products.find(
        {
            "is_active": True,
            "$or": [
                {"name": {"$regex": f"^{q}", "$options": "i"}},
                {"name": {"$regex": q, "$options": "i"}}
            ]
        },
        {"_id": 0, "id": 1, "name": 1, "image_url": 1, "slug": 1}
    ).limit(limit).to_list(limit)
    
    return products


@api_router.put("/products/reorder")
async def reorder_products(order_data: ProductOrderUpdate, current_user: dict = Depends(get_current_user)):
    for index, product_id in enumerate(order_data.product_ids):
        await db.products.update_one({"id": product_id}, {"$set": {"sort_order": index}})
    return {"message": "Products reordered successfully"}

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    # First try to find by slug
    product = await db.products.find_one({"slug": product_id}, {"_id": 0})
    if not product:
        # Then try by ID
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert datetime fields to ISO strings
    if "created_at" in product and isinstance(product["created_at"], datetime):
        product["created_at"] = product["created_at"].isoformat()
    if "updated_at" in product and isinstance(product["updated_at"], datetime):
        product["updated_at"] = product["updated_at"].isoformat()
    
    # Remove Discord webhooks from public API response (keep discord_webhooks as empty list for model validation)
    if "discord_webhooks" in product:
        product["discord_webhooks"] = []
    
    return product

@api_router.get("/admin/products/{product_id}", response_model=Product)
async def get_product_admin(product_id: str, current_user: dict = Depends(get_current_user)):
    """Admin endpoint that includes discord_webhooks"""
    # First try to find by slug
    product = await db.products.find_one({"slug": product_id}, {"_id": 0})
    if not product:
        # Then try by ID
        product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Convert datetime fields to ISO strings
    if "created_at" in product and isinstance(product["created_at"], datetime):
        product["created_at"] = product["created_at"].isoformat()
    if "updated_at" in product and isinstance(product["updated_at"], datetime):
        product["updated_at"] = product["updated_at"].isoformat()
    
    # Keep discord_webhooks for admin
    if "discord_webhooks" not in product:
        product["discord_webhooks"] = []
    
    return product

@api_router.get("/products/{product_id}/related")
async def get_related_products(product_id: str, limit: int = 4):
    """Get related products (same category or similar tags) - for 'Customers Also Bought' section"""
    # First get the current product
    product = await db.products.find_one({"$or": [{"slug": product_id}, {"id": product_id}]})
    if not product:
        return []
    
    related = []
    
    # Find products in same category
    same_category = await db.products.find({
        "category_id": product.get("category_id"),
        "id": {"$ne": product.get("id")},
        "is_active": True
    }, {"_id": 0}).limit(limit).to_list(limit)
    related.extend(same_category)
    
    # If not enough, find products with similar tags
    if len(related) < limit and product.get("tags"):
        existing_ids = [p.get("id") for p in related]
        existing_ids.append(product.get("id"))
        with_tags = await db.products.find({
            "tags": {"$in": product.get("tags", [])},
            "id": {"$nin": existing_ids},
            "is_active": True
        }, {"_id": 0}).limit(limit - len(related)).to_list(limit - len(related))
        related.extend(with_tags)
    
    # If still not enough, get any other products
    if len(related) < limit:
        existing_ids = [p.get("id") for p in related]
        existing_ids.append(product.get("id"))
        others = await db.products.find({
            "id": {"$nin": existing_ids},
            "is_active": True
        }, {"_id": 0}).limit(limit - len(related)).to_list(limit - len(related))
        related.extend(others)
    
    # Convert datetime fields for all products
    for prod in related:
        if "created_at" in prod and isinstance(prod["created_at"], datetime):
            prod["created_at"] = prod["created_at"].isoformat()
        if "updated_at" in prod and isinstance(prod["updated_at"], datetime):
            prod["updated_at"] = prod["updated_at"].isoformat()
    
    return related[:limit]

def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from product name"""
    import re
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    max_order = await db.products.find_one(sort=[("sort_order", -1)])
    next_order = (max_order.get("sort_order", 0) + 1) if max_order else 0

    product_dict = product_data.model_dump()
    product_dict["sort_order"] = next_order
    
    # Use custom slug if provided, otherwise auto-generate
    if product_data.slug and product_data.slug.strip():
        custom_slug = product_data.slug.strip().lower().replace(' ', '-')
        # Check if slug already exists
        existing_slug = await db.products.find_one({"slug": custom_slug})
        if existing_slug:
            raise HTTPException(status_code=400, detail="This URL slug is already in use. Please choose a different one.")
        product_dict["slug"] = custom_slug
    else:
        product_dict["slug"] = generate_slug(product_data.name)
    
    product = Product(**product_dict)
    await db.products.insert_one(product.model_dump())
    return product

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.products.find_one({"id": product_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_data.model_dump()
    
    # Use custom slug if provided, otherwise keep existing or auto-generate
    if product_data.slug and product_data.slug.strip():
        custom_slug = product_data.slug.strip().lower().replace(' ', '-')
        # Check if slug is already used by another product
        existing_slug = await db.products.find_one({"slug": custom_slug, "id": {"$ne": product_id}})
        if existing_slug:
            raise HTTPException(status_code=400, detail="This URL slug is already in use. Please choose a different one.")
        update_data["slug"] = custom_slug
    else:
        # Keep existing slug or generate new one
        update_data["slug"] = existing.get("slug") or generate_slug(product_data.name)
    
    await db.products.update_one({"id": product_id}, {"$set": update_data})
    updated = await db.products.find_one({"id": product_id}, {"_id": 0})
    return updated

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}

# ==================== REVIEW ROUTES ====================

@api_router.get("/reviews", response_model=List[Review])
async def get_reviews():
    # Limit to 20 most recent reviews for display
    reviews = await db.reviews.find({}, {"_id": 0}).sort("review_date", -1).to_list(20)
    
    # Convert datetime fields to ISO strings
    for review in reviews:
        if "created_at" in review and isinstance(review["created_at"], datetime):
            review["created_at"] = review["created_at"].isoformat()
        if "review_date" in review and isinstance(review["review_date"], datetime):
            review["review_date"] = review["review_date"].isoformat()
    
    return reviews

@api_router.post("/reviews", response_model=Review)
async def create_review(review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    review = Review(
        reviewer_name=review_data.reviewer_name,
        rating=review_data.rating,
        comment=review_data.comment,
        review_date=review_data.review_date or datetime.now(timezone.utc).isoformat()
    )
    await db.reviews.insert_one(review.model_dump())
    return review

@api_router.put("/reviews/{review_id}", response_model=Review)
async def update_review(review_id: str, review_data: ReviewCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.reviews.find_one({"id": review_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data = review_data.model_dump()
    update_data["review_date"] = review_data.review_date or existing.get("review_date")
    await db.reviews.update_one({"id": review_id}, {"$set": update_data})
    updated = await db.reviews.find_one({"id": review_id}, {"_id": 0})
    return updated

@api_router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.reviews.delete_one({"id": review_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted"}

# ==================== TRUSTPILOT SYNC ====================

TRUSTPILOT_DOMAIN = "gameshopnepal.com"
TRUSTPILOT_API_KEY = os.environ.get("TRUSTPILOT_API_KEY", "")

async def get_trustpilot_business_unit_id():
    """Get the business unit ID from Trustpilot using the domain"""
    cached = await db.trustpilot_config.find_one({"key": "business_unit_id"})
    if cached and cached.get("value"):
        return cached["value"]
    
    # Try to find business unit ID via API or scraping
    async with httpx.AsyncClient() as client:
        try:
            # First try the public find endpoint (may need API key)
            if TRUSTPILOT_API_KEY:
                response = await client.get(
                    f"https://api.trustpilot.com/v1/business-units/find?name={TRUSTPILOT_DOMAIN}",
                    headers={"apikey": TRUSTPILOT_API_KEY},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    buid = data.get("id")
                    if buid:
                        await db.trustpilot_config.update_one(
                            {"key": "business_unit_id"},
                            {"$set": {"key": "business_unit_id", "value": buid}},
                            upsert=True
                        )
                        return buid
        except Exception as e:
            logger.error(f"Error getting business unit ID: {e}")
    
    return None

async def fetch_trustpilot_reviews_from_page():
    """Scrape reviews from Trustpilot page as fallback"""
    reviews = []
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://www.trustpilot.com/review/{TRUSTPILOT_DOMAIN}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=15.0
            )
            if response.status_code == 200:
                import re
                import json
                
                # Try to find JSON-LD data in the page
                html = response.text
                
                # Look for review data in script tags
                json_ld_pattern = r'<script type="application/ld\+json"[^>]*>(.*?)</script>'
                matches = re.findall(json_ld_pattern, html, re.DOTALL)
                
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, dict) and data.get("@type") == "LocalBusiness":
                            if "review" in data:
                                for review in data["review"]:
                                    reviews.append({
                                        "reviewer_name": review.get("author", {}).get("name", "Anonymous"),
                                        "rating": int(review.get("reviewRating", {}).get("ratingValue", 5)),
                                        "comment": review.get("reviewBody", ""),
                                        "review_date": review.get("datePublished", datetime.now(timezone.utc).isoformat())
                                    })
                    except json.JSONDecodeError:
                        continue
                
                # Also try to parse from __NEXT_DATA__
                next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
                next_matches = re.findall(next_data_pattern, html, re.DOTALL)
                
                for match in next_matches:
                    try:
                        data = json.loads(match)
                        props = data.get("props", {}).get("pageProps", {})
                        review_list = props.get("reviews", [])
                        
                        for review in review_list:
                            consumer = review.get("consumer", {})
                            # Get the published date from dates object
                            dates = review.get("dates", {})
                            published_date = dates.get("publishedDate") or dates.get("experiencedDate")
                            
                            reviews.append({
                                "reviewer_name": consumer.get("displayName", "Anonymous"),
                                "rating": review.get("rating", 5),
                                "comment": review.get("text", review.get("title", "")),
                                "review_date": published_date or datetime.now(timezone.utc).isoformat()
                            })
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error scraping Trustpilot: {e}")
    
    return reviews

@api_router.post("/reviews/sync-trustpilot")
async def sync_trustpilot_reviews(current_user: dict = Depends(get_current_user)):
    """Sync reviews from Trustpilot to the database"""
    synced_count = 0
    
    try:
        # Try scraping the Trustpilot page
        trustpilot_reviews = await fetch_trustpilot_reviews_from_page()
        
        for tp_review in trustpilot_reviews:
            # Check if this review already exists (by reviewer name and comment)
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
                    "source": "trustpilot"
                }
                await db.reviews.insert_one(review)
                synced_count += 1
        
        # Update last sync time
        await db.trustpilot_config.update_one(
            {"key": "last_sync"},
            {"$set": {"key": "last_sync", "value": datetime.now(timezone.utc).isoformat()}},
            upsert=True
        )
        
        return {
            "success": True,
            "synced_count": synced_count,
            "total_found": len(trustpilot_reviews),
            "message": f"Synced {synced_count} new reviews from Trustpilot"
        }
        
    except Exception as e:
        logger.error(f"Error syncing Trustpilot reviews: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync reviews: {str(e)}")

@api_router.get("/reviews/trustpilot-status")
async def get_trustpilot_status(current_user: dict = Depends(get_current_user)):
    """Get Trustpilot sync status"""
    last_sync = await db.trustpilot_config.find_one({"key": "last_sync"})
    tp_review_count = await db.reviews.count_documents({"source": "trustpilot"})
    
    return {
        "domain": TRUSTPILOT_DOMAIN,
        "last_sync": last_sync.get("value") if last_sync else None,
        "trustpilot_reviews_count": tp_review_count,
        "api_key_configured": bool(TRUSTPILOT_API_KEY)
    }

@api_router.get("/faqs", response_model=List[FAQItem])
async def get_faqs():
    faqs = await db.faqs.find({}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return faqs

@api_router.post("/faqs", response_model=FAQItem)
async def create_faq(faq_data: FAQItemCreate, current_user: dict = Depends(get_current_user)):
    max_order = await db.faqs.find_one(sort=[("sort_order", -1)])
    next_order = (max_order.get("sort_order", 0) + 1) if max_order else 0

    faq = FAQItem(question=faq_data.question, answer=faq_data.answer, sort_order=next_order)
    await db.faqs.insert_one(faq.model_dump())
    return faq

@api_router.put("/faqs/reorder")
async def reorder_faqs(request: Request, current_user: dict = Depends(get_current_user)):
    faq_ids = await request.json()
    for index, faq_id in enumerate(faq_ids):
        await db.faqs.update_one({"id": faq_id}, {"$set": {"sort_order": index}})
    return {"message": "FAQs reordered successfully"}

@api_router.put("/faqs/{faq_id}", response_model=FAQItem)
async def update_faq(faq_id: str, faq_data: FAQItemCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.faqs.find_one({"id": faq_id})
    if not existing:
        raise HTTPException(status_code=404, detail="FAQ not found")

    await db.faqs.update_one({"id": faq_id}, {"$set": faq_data.model_dump()})
    updated = await db.faqs.find_one({"id": faq_id}, {"_id": 0})
    return updated

@api_router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.faqs.delete_one({"id": faq_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "FAQ deleted"}

# ==================== PAGE ROUTES ====================

@api_router.get("/pages/{page_key}")
async def get_page(page_key: str):
    page = await db.pages.find_one({"page_key": page_key}, {"_id": 0})
    if not page:
        defaults = {
            "about": {"title": "About Us", "content": "<p>Welcome to GameShop Nepal - Your trusted source for digital products since 2021.</p>"},
            "terms": {"title": "Terms and Conditions", "content": "<p>Terms and conditions content here.</p>"},
            "faq": {"title": "FAQ", "content": ""}
        }
        return {"page_key": page_key, **defaults.get(page_key, {"title": page_key.title(), "content": ""})}
    return page

@api_router.put("/pages/{page_key}")
async def update_page(page_key: str, title: str, content: str, current_user: dict = Depends(get_current_user)):
    page_data = {
        "page_key": page_key,
        "title": title,
        "content": content,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.pages.update_one({"page_key": page_key}, {"$set": page_data}, upsert=True)
    return page_data

# ==================== SOCIAL LINK ROUTES ====================

@api_router.get("/social-links")
async def get_social_links():
    """Get all social links as an array"""
    links = await db.social_links.find({}, {"_id": 0}).to_list(100)
    return links

@api_router.post("/social-links", response_model=SocialLink)
async def create_social_link(link_data: SocialLinkCreate, current_user: dict = Depends(get_current_user)):
    link = SocialLink(**link_data.model_dump())
    await db.social_links.insert_one(link.model_dump())
    return link

@api_router.put("/social-links/{link_id}", response_model=SocialLink)
async def update_social_link(link_id: str, link_data: SocialLinkCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.social_links.find_one({"id": link_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Social link not found")

    await db.social_links.update_one({"id": link_id}, {"$set": link_data.model_dump()})
    updated = await db.social_links.find_one({"id": link_id}, {"_id": 0})
    return updated

@api_router.delete("/social-links/{link_id}")
async def delete_social_link(link_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.social_links.delete_one({"id": link_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Social link not found")
    return {"message": "Social link deleted"}

# ==================== CLEAR DATA ====================

@api_router.post("/clear-products")
async def clear_products(current_user: dict = Depends(get_current_user)):
    await db.products.delete_many({})
    await db.categories.delete_many({})
    return {"message": "All products and categories cleared"}

# ==================== SEED DATA ====================

@api_router.post("/seed")
async def seed_data():
    social_data = [
        {"id": "fb", "platform": "Facebook", "url": "https://facebook.com/gameshopnepal", "icon": "facebook"},
        {"id": "ig", "platform": "Instagram", "url": "https://instagram.com/gameshopnepal", "icon": "instagram"},
        {"id": "tt", "platform": "TikTok", "url": "https://tiktok.com/@gameshopnepal", "icon": "tiktok"},
        {"id": "wa", "platform": "WhatsApp", "url": "https://wa.me/9779743488871", "icon": "whatsapp"},
    ]

    for link in social_data:
        await db.social_links.update_one({"id": link["id"]}, {"$set": link}, upsert=True)

    reviews_data = [
        {"id": "rev1", "reviewer_name": "Sujan Thapa", "rating": 5, "comment": "Fast delivery and genuine products. Got my Netflix subscription within minutes!", "review_date": "2025-01-10T10:00:00Z", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": "rev2", "reviewer_name": "Anisha Sharma", "rating": 5, "comment": "Best prices in Nepal for digital products. Highly recommended!", "review_date": "2025-01-08T14:30:00Z", "created_at": datetime.now(timezone.utc).isoformat()},
        {"id": "rev3", "reviewer_name": "Rohan KC", "rating": 5, "comment": "Bought PUBG UC, instant delivery. Will buy again!", "review_date": "2025-01-05T09:15:00Z", "created_at": datetime.now(timezone.utc).isoformat()},
    ]

    for rev in reviews_data:
        await db.reviews.update_one({"id": rev["id"]}, {"$set": rev}, upsert=True)

    default_faqs = [
        {"id": "faq1", "question": "How do I place an order?", "answer": "Simply browse our products, select the plan you want, and click 'Order Now'. This will redirect you to WhatsApp where you can complete your order.", "sort_order": 0},
        {"id": "faq2", "question": "How long does delivery take?", "answer": "Most products are delivered instantly within minutes after payment confirmation.", "sort_order": 1},
        {"id": "faq3", "question": "What payment methods do you accept?", "answer": "We accept eSewa, Khalti, bank transfer, and other local payment methods.", "sort_order": 2},
        {"id": "faq4", "question": "Are your products genuine?", "answer": "Yes! All our products are 100% genuine and sourced directly from authorized channels.", "sort_order": 3},
    ]

    for faq in default_faqs:
        await db.faqs.update_one({"id": faq["id"]}, {"$set": faq}, upsert=True)

    return {"message": "Data seeded successfully"}

# Order creation models
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

@api_router.post("/orders/create")
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

@api_router.get("/orders")
async def get_local_orders(current_user: dict = Depends(get_current_user)):
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

# ==================== PAYMENT METHODS ====================

class PaymentMethod(BaseModel):
    id: Optional[str] = None
    name: str
    image_url: str  # Logo/icon
    qr_code_url: Optional[str] = None  # Legacy single QR code (kept for backwards compatibility)
    qr_codes: Optional[List[dict]] = []  # Multiple QR codes: [{"url": "...", "label": "QR 1"}, ...]
    merchant_name: Optional[str] = None
    phone_number: Optional[str] = None
    instructions: Optional[str] = None  # Payment instructions text
    is_active: bool = True
    sort_order: int = 0

@api_router.get("/payment-methods")
async def get_payment_methods():
    # Check both 'enabled' and 'is_active' for backwards compatibility
    methods = await db.payment_methods.find({
        "$or": [{"enabled": True}, {"is_active": True}]
    }).sort([("sort_order", 1), ("display_order", 1)]).to_list(100)
    for m in methods:
        m.pop("_id", None)
    return methods

@api_router.get("/payment-methods/all")
async def get_all_payment_methods(current_user: dict = Depends(get_current_user)):
    methods = await db.payment_methods.find().sort("sort_order", 1).to_list(100)
    for m in methods:
        m.pop("_id", None)
    return methods

@api_router.get("/payment-methods/{method_id}")
async def get_payment_method(method_id: str):
    method = await db.payment_methods.find_one({"id": method_id}, {"_id": 0})
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    return method

@api_router.post("/payment-methods")
async def create_payment_method(method: PaymentMethod, current_user: dict = Depends(get_current_user)):
    method_dict = method.model_dump()
    method_dict["id"] = str(uuid.uuid4())
    await db.payment_methods.insert_one(method_dict)
    method_dict.pop("_id", None)
    return method_dict

@api_router.put("/payment-methods/{method_id}")
async def update_payment_method(method_id: str, method: PaymentMethod, current_user: dict = Depends(get_current_user)):
    method_dict = method.model_dump()
    method_dict["id"] = method_id
    await db.payment_methods.update_one({"id": method_id}, {"$set": method_dict})
    return method_dict

@api_router.delete("/payment-methods/{method_id}")
async def delete_payment_method(method_id: str, current_user: dict = Depends(get_current_user)):
    await db.payment_methods.delete_one({"id": method_id})
    return {"message": "Payment method deleted"}

# ==================== ORDER PAYMENT SCREENSHOT ====================

class PaymentScreenshotUpload(BaseModel):
    screenshot_url: str
    payment_method: Optional[str] = None

@api_router.post("/orders/{order_id}/payment-screenshot")
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
            await use_credits(customer_email, credits_used, order_id)
            credits_deducted = credits_used
            logger.info(f"Deducted {credits_used} credits from {customer_email} for order {order_id}")
        except Exception as e:
            logger.warning(f"Failed to deduct credits for order {order_id}: {e}")
    
    await db.orders.update_one(
        {"id": order_id},
        {"$set": {
            "payment_screenshot": data.screenshot_url,
            "payment_method": data.payment_method,
            "payment_uploaded_at": datetime.now(timezone.utc).isoformat(),
            "status": "Confirmed",
            "invoice_url": invoice_url,
            "credits_pending": False,
            "credits_deducted": credits_deducted > 0
        }}
    )
    
    # Send Discord webhook notifications for products with webhooks
    try:
        # Get updated order
        updated_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        
        # Collect all Discord webhooks from order items
        all_webhooks = []
        product_names = []
        
        for item in updated_order.get('items', []):
            product_id = item.get('product_id')
            if product_id:
                # Fetch product to get webhooks
                product = await db.products.find_one({"id": product_id})
                if product and product.get('discord_webhooks'):
                    webhooks = product.get('discord_webhooks', [])
                    all_webhooks.extend(webhooks)
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

@api_router.post("/orders/{order_id}/complete")
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
            
            credit_result = await award_credits_for_order(order_id, customer_email, order_total)
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
    
    # Send invoice email to customer if email exists
    if customer_email:
        try:
            site_url = os.environ.get("SITE_URL", "https://gameshopnepal.com")
            invoice_url = f"{site_url}/invoice/{order_id}"
            trustpilot_url = "https://www.trustpilot.com/evaluate/gameshopnepal.com"
            
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
                        <a href="{trustpilot_url}" style="display: inline-block; background: #00b67a; color: #fff; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            ⭐ Leave a Review on Trustpilot
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; text-align: center; margin-top: 30px;">
                        Thank you for shopping with GameShop Nepal!
                    </p>
                </div>
            </div>
            """
            text = f"Order #{order_id[:8]} Complete!\n\nYour order has been completed.\n{'You earned Rs ' + str(int(credits_awarded)) + ' in store credits!' if credits_awarded > 0 else ''}\nView Invoice: {invoice_url}\nLeave a Review: {trustpilot_url}"
            
            from email_service import send_email
            send_email(customer_email, subject, html, text)
        except Exception as e:
            print(f"Failed to send invoice email: {e}")
    
    response = {"message": "Order marked as completed", "order_id": order_id}
    if credits_awarded > 0:
        response["credits_awarded"] = credits_awarded
    return response


@api_router.delete("/orders/{order_id}")
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

@api_router.post("/orders/bulk-delete")
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

@api_router.get("/invoice/{order_id}")
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

# ==================== NOTIFICATION BAR ====================

class NotificationBar(BaseModel):
    id: Optional[str] = None
    text: str
    link: Optional[str] = None
    is_active: bool = True
    bg_color: Optional[str] = "#F5A623"
    text_color: Optional[str] = "#000000"

@api_router.get("/notification-bar")
async def get_notification_bar():
    notification = await db.notification_bar.find_one({"is_active": True})
    if notification:
        notification.pop("_id", None)
    return notification

@api_router.put("/notification-bar")
async def update_notification_bar(notification: NotificationBar, current_user: dict = Depends(get_current_user)):
    notification_dict = notification.model_dump()
    notification_dict["id"] = "main"
    await db.notification_bar.update_one({"id": "main"}, {"$set": notification_dict}, upsert=True)
    return notification_dict

# ==================== BLOG POSTS ====================

class BlogPost(BaseModel):
    id: Optional[str] = None
    title: str
    slug: Optional[str] = None
    excerpt: str
    content: str
    image_url: Optional[str] = None
    is_published: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@api_router.get("/blog")
async def get_blog_posts():
    posts = await db.blog_posts.find({"is_published": True}).sort("created_at", -1).to_list(100)
    for p in posts:
        p.pop("_id", None)
    return posts

@api_router.get("/blog/all/admin")
async def get_all_blog_posts(current_user: dict = Depends(get_current_user)):
    posts = await db.blog_posts.find().sort("created_at", -1).to_list(100)
    for p in posts:
        p.pop("_id", None)
    return posts

@api_router.get("/blog/{slug}")
async def get_blog_post(slug: str):
    post = await db.blog_posts.find_one({"slug": slug, "is_published": True})
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    post.pop("_id", None)
    return post

@api_router.post("/blog")
async def create_blog_post(post: BlogPost, current_user: dict = Depends(get_current_user)):
    post_dict = post.model_dump()
    post_dict["id"] = str(uuid.uuid4())
    post_dict["slug"] = post_dict["slug"] or post_dict["title"].lower().replace(" ", "-").replace("?", "").replace("!", "")
    post_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    post_dict["updated_at"] = post_dict["created_at"]
    await db.blog_posts.insert_one(post_dict)
    post_dict.pop("_id", None)
    return post_dict

@api_router.put("/blog/{post_id}")
async def update_blog_post(post_id: str, post: BlogPost, current_user: dict = Depends(get_current_user)):
    post_dict = post.model_dump()
    post_dict["id"] = post_id
    post_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.blog_posts.update_one({"id": post_id}, {"$set": post_dict})
    return post_dict

@api_router.delete("/blog/{post_id}")
async def delete_blog_post(post_id: str, current_user: dict = Depends(get_current_user)):
    await db.blog_posts.delete_one({"id": post_id})
    return {"message": "Blog post deleted"}

# ==================== SITE SETTINGS ====================

@api_router.get("/settings")
async def get_site_settings():
    settings = await db.site_settings.find_one({"id": "main"})
    if not settings:
        settings = {
            "id": "main", 
            "notification_bar_enabled": True, 
            "chat_enabled": True,
            "service_charge": 0,
            "tax_percentage": 0,
            "tax_label": "Tax"
        }
    settings.pop("_id", None)
    return settings

@api_router.put("/settings")
async def update_site_settings(settings: dict, current_user: dict = Depends(get_current_user)):
    settings["id"] = "main"
    await db.site_settings.update_one({"id": "main"}, {"$set": settings}, upsert=True)
    return settings

# ==================== PROMO CODES ====================

@api_router.get("/promo-codes")
async def get_promo_codes(current_user: dict = Depends(get_current_user)):
    codes = await db.promo_codes.find().sort("created_at", -1).to_list(100)
    for c in codes:
        c.pop("_id", None)
    return codes

@api_router.post("/promo-codes")
async def create_promo_code(code_data: PromoCodeCreate, current_user: dict = Depends(get_current_user)):
    # Check if code already exists
    existing = await db.promo_codes.find_one({"code": code_data.code.upper()})
    if existing:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    
    code = PromoCode(
        code=code_data.code.upper(),
        discount_type=code_data.discount_type,
        discount_value=code_data.discount_value,
        min_order_amount=code_data.min_order_amount,
        max_uses=code_data.max_uses,
        max_uses_per_customer=code_data.max_uses_per_customer,
        is_active=code_data.is_active,
        expiry_date=code_data.expiry_date,
        applicable_categories=code_data.applicable_categories,
        applicable_products=code_data.applicable_products,
        first_time_only=code_data.first_time_only,
        buy_quantity=code_data.buy_quantity,
        get_quantity=code_data.get_quantity,
        auto_apply=code_data.auto_apply,
        stackable=code_data.stackable
    )
    await db.promo_codes.insert_one(code.model_dump())
    result = code.model_dump()
    result.pop("_id", None)
    return result

@api_router.put("/promo-codes/{code_id}")
async def update_promo_code(code_id: str, code_data: PromoCodeCreate, current_user: dict = Depends(get_current_user)):
    existing = await db.promo_codes.find_one({"id": code_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Promo code not found")
    
    update_data = code_data.model_dump()
    update_data["code"] = update_data["code"].upper()
    await db.promo_codes.update_one({"id": code_id}, {"$set": update_data})
    updated = await db.promo_codes.find_one({"id": code_id}, {"_id": 0})
    return updated

@api_router.delete("/promo-codes/{code_id}")
async def delete_promo_code(code_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.promo_codes.delete_one({"id": code_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return {"message": "Promo code deleted"}

@api_router.post("/promo-codes/validate")
async def validate_promo_code(
    code: str, 
    subtotal: float, 
    cart_items: List[dict] = [], 
    customer_email: Optional[str] = None
):
    """Validate a promo code with advanced rules - requires customer login"""
    # Require customer to be logged in
    if not customer_email:
        raise HTTPException(status_code=401, detail="Please login to use promo codes")
    
    promo = await db.promo_codes.find_one({"code": code.upper(), "is_active": True})
    if not promo:
        raise HTTPException(status_code=400, detail="Invalid or expired promo code")
    
    # Check expiry date
    if promo.get("expiry_date"):
        expiry = datetime.fromisoformat(promo["expiry_date"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=400, detail="Promo code has expired")
    
    # Check minimum order amount
    if promo.get("min_order_amount", 0) > subtotal:
        raise HTTPException(status_code=400, detail=f"Minimum order amount is Rs {promo['min_order_amount']}")
    
    # Check max uses (global)
    if promo.get("max_uses") and promo.get("used_count", 0) >= promo["max_uses"]:
        raise HTTPException(status_code=400, detail="Promo code has reached maximum uses")
    
    # Check max uses per customer (user-specific limit)
    max_per_user = promo.get("max_uses_per_customer") or promo.get("max_uses_per_user")
    if max_per_user:
        customer_usage = await db.promo_usage.count_documents({
            "promo_code": code.upper(),
            "customer_email": customer_email.lower()
        })
        if customer_usage >= max_per_user:
            raise HTTPException(status_code=400, detail=f"You have reached the maximum {max_per_user} uses for this promo code")
    
    # Check first-time buyer restriction
    if promo.get("first_time_only"):
        previous_orders = await db.orders.count_documents({"customer_email": customer_email.lower()})
        if previous_orders > 0:
            raise HTTPException(status_code=400, detail="This promo code is only for first-time buyers")
    
    # Check category/product restrictions
    if promo.get("applicable_categories") or promo.get("applicable_products"):
        cart_valid = False
        for item in cart_items:
            product_id = item.get("product_id")
            if product_id:
                product = await db.products.find_one({"id": product_id})
                if product:
                    # Check if product matches
                    if promo.get("applicable_products") and product_id in promo["applicable_products"]:
                        cart_valid = True
                        break
                    # Check if category matches
                    if promo.get("applicable_categories") and product.get("category_id") in promo["applicable_categories"]:
                        cart_valid = True
                        break
        
        if not cart_valid:
            raise HTTPException(status_code=400, detail="This promo code is not applicable to items in your cart")
    
    # Calculate discount
    discount = 0
    discount_details = {}
    
    if promo["discount_type"] == "percentage":
        discount = subtotal * (promo["discount_value"] / 100)
        discount_details = {
            "type": "percentage",
            "value": promo["discount_value"],
            "description": f"{promo['discount_value']}% off"
        }
    elif promo["discount_type"] == "fixed":
        discount = min(promo["discount_value"], subtotal)
        discount_details = {
            "type": "fixed",
            "value": promo["discount_value"],
            "description": f"Rs {promo['discount_value']} off"
        }
    elif promo["discount_type"] == "buy_x_get_y":
        buy_qty = promo.get("buy_quantity", 0)
        get_qty = promo.get("get_quantity", 0)
        discount_details = {
            "type": "buy_x_get_y",
            "buy_quantity": buy_qty,
            "get_quantity": get_qty,
            "description": f"Buy {buy_qty}, Get {get_qty} Free"
        }
    elif promo["discount_type"] == "free_shipping":
        discount_details = {
            "type": "free_shipping",
            "description": "Free Shipping"
        }
    
    return {
        "valid": True,
        "code": promo["code"],
        "discount_type": promo["discount_type"],
        "discount_value": promo["discount_value"],
        "discount_amount": round(discount, 2),
        "details": discount_details,
        "stackable": promo.get("stackable", False),
        "message": f"Promo code applied! {discount_details.get('description', '')}"
    }

@api_router.get("/promo-codes/auto-apply")
async def get_auto_apply_promos(subtotal: float, customer_email: Optional[str] = None):
    """Get all auto-apply promo codes that match the criteria"""
    query = {"is_active": True, "auto_apply": True}
    
    # Check expiry
    now = datetime.now(timezone.utc).isoformat()
    query["$or"] = [
        {"expiry_date": None},
        {"expiry_date": {"$gt": now}}
    ]
    
    promos = await db.promo_codes.find(query, {"_id": 0}).to_list(100)
    
    applicable_promos = []
    for promo in promos:
        try:
            # Validate each promo
            validation = await validate_promo_code(
                promo["code"], 
                subtotal, 
                [], 
                customer_email
            )
            applicable_promos.append({
                "code": promo["code"],
                "discount_amount": validation["discount_amount"],
                "description": validation["details"]["description"]
            })
        except Exception:
            continue
    
    return applicable_promos

@api_router.post("/promo-codes/record-usage")
async def record_promo_usage(promo_code: str, order_id: str, customer_email: Optional[str] = None):
    """Record promo code usage"""
    # Increment usage count
    await db.promo_codes.update_one(
        {"code": promo_code.upper()},
        {"$inc": {"used_count": 1}}
    )
    
    # Record individual usage
    usage_record = {
        "id": str(uuid.uuid4()),
        "promo_code": promo_code.upper(),
        "order_id": order_id,
        "customer_email": customer_email,
        "used_at": datetime.now(timezone.utc).isoformat()
    }
    await db.promo_usage.insert_one(usage_record)
    
    return {"message": "Promo usage recorded"}


# ==================== STORE CREDITS ====================

@api_router.get("/credits/settings")
async def get_credit_settings():
    """Get credit system settings"""
    settings = await db.credit_settings.find_one({"id": "main"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "main",
            "cashback_percentage": 5.0,
            "is_enabled": True,
            "eligible_categories": [],
            "eligible_products": [],
            "min_order_amount": 0,
            "usable_categories": [],
            "usable_products": []
        }
    return settings

@api_router.put("/credits/settings")
async def update_credit_settings(settings: CreditSettings, current_user: dict = Depends(get_current_user)):
    """Update credit system settings (admin only)"""
    settings_dict = settings.model_dump()
    settings_dict["id"] = "main"
    await db.credit_settings.update_one({"id": "main"}, {"$set": settings_dict}, upsert=True)
    return settings_dict

@api_router.get("/credits/balance")
async def get_customer_credit_balance(email: str):
    """Get customer's credit balance"""
    customer = await db.customers.find_one({"email": email})
    if not customer:
        return {"credit_balance": 0}
    return {"credit_balance": customer.get("credit_balance", 0)}

@api_router.post("/credits/adjust")
async def adjust_customer_credits(data: CustomerCreditUpdate, current_user: dict = Depends(get_current_user)):
    """Manually adjust customer credits (admin only)"""
    customer = await db.customers.find_one({"id": data.customer_id})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    current_balance = customer.get("credit_balance", 0)
    new_balance = max(0, current_balance + data.amount)  # Don't go below 0
    
    await db.customers.update_one(
        {"id": data.customer_id},
        {"$set": {"credit_balance": new_balance}}
    )
    
    # Log the credit transaction
    credit_log = {
        "id": str(uuid.uuid4()),
        "customer_id": data.customer_id,
        "customer_email": customer.get("email"),
        "amount": data.amount,
        "reason": data.reason,
        "balance_before": current_balance,
        "balance_after": new_balance,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.get("id", "admin")
    }
    await db.credit_logs.insert_one(credit_log)
    
    return {
        "success": True,
        "previous_balance": current_balance,
        "new_balance": new_balance,
        "message": f"Credit {'added' if data.amount > 0 else 'deducted'} successfully"
    }

@api_router.get("/credits/logs/{customer_id}")
async def get_customer_credit_logs(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get credit transaction history for a customer"""
    logs = await db.credit_logs.find({"customer_id": customer_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return logs

@api_router.post("/credits/award")
async def award_credits_for_order(order_id: str, customer_email: str, order_total: float):
    """Award cashback credits for a completed order"""
    settings = await db.credit_settings.find_one({"id": "main"})
    if not settings or not settings.get("is_enabled", True):
        return {"credits_awarded": 0, "message": "Credit system is disabled"}
    
    # Check minimum order amount
    if order_total < settings.get("min_order_amount", 0):
        return {"credits_awarded": 0, "message": "Order below minimum amount for credits"}
    
    # Calculate credits
    cashback_percentage = settings.get("cashback_percentage", 5.0)
    credits_to_award = round(order_total * (cashback_percentage / 100), 2)
    
    # Find or create customer
    customer = await db.customers.find_one({"email": customer_email})
    if customer:
        current_balance = customer.get("credit_balance", 0)
        new_balance = current_balance + credits_to_award
        await db.customers.update_one(
            {"email": customer_email},
            {"$set": {"credit_balance": new_balance}}
        )
        
        # Log the credit award
        credit_log = {
            "id": str(uuid.uuid4()),
            "customer_id": customer.get("id"),
            "customer_email": customer_email,
            "amount": credits_to_award,
            "reason": f"Cashback for order {order_id}",
            "balance_before": current_balance,
            "balance_after": new_balance,
            "order_id": order_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.credit_logs.insert_one(credit_log)
        
        return {"credits_awarded": credits_to_award, "new_balance": new_balance}
    
    return {"credits_awarded": 0, "message": "Customer not found"}

@api_router.post("/credits/use")
async def use_credits(customer_email: str, amount: float, order_id: str):
    """Deduct credits when used in an order"""
    customer = await db.customers.find_one({"email": customer_email})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    current_balance = customer.get("credit_balance", 0)
    if amount > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient credit balance")
    
    new_balance = current_balance - amount
    await db.customers.update_one(
        {"email": customer_email},
        {"$set": {"credit_balance": new_balance}}
    )
    
    # Log the credit usage
    credit_log = {
        "id": str(uuid.uuid4()),
        "customer_id": customer.get("id"),
        "customer_email": customer_email,
        "amount": -amount,
        "reason": f"Used for order {order_id}",
        "balance_before": current_balance,
        "balance_after": new_balance,
        "order_id": order_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.credit_logs.insert_one(credit_log)
    
    return {"success": True, "amount_used": amount, "new_balance": new_balance}


# ==================== BUNDLE DEALS ====================

class BundleProduct(BaseModel):
    product_id: str
    variation_id: Optional[str] = None

class BundleCreate(BaseModel):
    name: str
    description: str = ""
    image_url: str = ""
    products: List[BundleProduct]
    original_price: float
    bundle_price: float
    is_active: bool = True
    sort_order: int = 0

class Bundle(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str = ""
    description: str = ""
    image_url: str = ""
    products: List[dict] = []
    original_price: float
    bundle_price: float
    discount_percentage: float = 0
    is_active: bool = True
    sort_order: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@api_router.get("/bundles")
async def get_bundles():
    """Get all active bundles with populated product details"""
    bundles = await db.bundles.find({"is_active": True}).sort("sort_order", 1).to_list(100)
    
    # Populate product details for each bundle
    for bundle in bundles:
        bundle.pop("_id", None)
        populated_products = []
        for bp in bundle.get("products", []):
            product = await db.products.find_one({"id": bp.get("product_id")}, {"_id": 0})
            if product:
                populated_products.append({
                    "product": product,
                    "variation_id": bp.get("variation_id")
                })
        bundle["populated_products"] = populated_products
    
    return bundles

@api_router.get("/bundles/all")
async def get_all_bundles(current_user: dict = Depends(get_current_user)):
    """Get all bundles for admin"""
    bundles = await db.bundles.find().sort("sort_order", 1).to_list(100)
    for b in bundles:
        b.pop("_id", None)
    return bundles

@api_router.post("/bundles")
async def create_bundle(bundle_data: BundleCreate, current_user: dict = Depends(get_current_user)):
    slug = bundle_data.name.lower().replace(" ", "-").replace("&", "and")
    discount_pct = round(((bundle_data.original_price - bundle_data.bundle_price) / bundle_data.original_price) * 100, 1) if bundle_data.original_price > 0 else 0
    
    bundle = Bundle(
        name=bundle_data.name,
        slug=slug,
        description=bundle_data.description,
        image_url=bundle_data.image_url,
        products=[p.model_dump() for p in bundle_data.products],
        original_price=bundle_data.original_price,
        bundle_price=bundle_data.bundle_price,
        discount_percentage=discount_pct,
        is_active=bundle_data.is_active,
        sort_order=bundle_data.sort_order
    )
    
    await db.bundles.insert_one(bundle.model_dump())
    result = bundle.model_dump()
    return result

@api_router.put("/bundles/{bundle_id}")
async def update_bundle(bundle_id: str, bundle_data: BundleCreate, current_user: dict = Depends(get_current_user)):
    slug = bundle_data.name.lower().replace(" ", "-").replace("&", "and")
    discount_pct = round(((bundle_data.original_price - bundle_data.bundle_price) / bundle_data.original_price) * 100, 1) if bundle_data.original_price > 0 else 0
    
    update_data = {
        "name": bundle_data.name,
        "slug": slug,
        "description": bundle_data.description,
        "image_url": bundle_data.image_url,
        "products": [p.model_dump() for p in bundle_data.products],
        "original_price": bundle_data.original_price,
        "bundle_price": bundle_data.bundle_price,
        "discount_percentage": discount_pct,
        "is_active": bundle_data.is_active,
        "sort_order": bundle_data.sort_order
    }
    
    await db.bundles.update_one({"id": bundle_id}, {"$set": update_data})
    updated = await db.bundles.find_one({"id": bundle_id}, {"_id": 0})
    return updated

@api_router.delete("/bundles/{bundle_id}")
async def delete_bundle(bundle_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.bundles.delete_one({"id": bundle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return {"message": "Bundle deleted"}

# ==================== RECENT PURCHASES (Live Ticker) ====================

# Nepal cities for random location
NEPAL_CITIES = ["Kathmandu", "Pokhara", "Lalitpur", "Biratnagar", "Bharatpur", "Birgunj", "Dharan", "Butwal", "Hetauda", "Bhaktapur", "Janakpur", "Nepalgunj", "Itahari", "Dhangadhi", "Tulsipur"]

@api_router.get("/recent-purchases")
async def get_recent_purchases(limit: int = 10):
    """Get recent purchases for live ticker - mix of real orders and simulated"""
    purchases = []
    
    # Get real recent orders (last 24 hours)
    yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    real_orders = await db.orders.find(
        {"created_at": {"$gte": yesterday}},
        {"_id": 0, "customer_name": 1, "items_text": 1, "created_at": 1}
    ).sort("created_at", -1).limit(5).to_list(5)
    
    for order in real_orders:
        # Mask customer name for privacy (show first name only)
        name_parts = order.get("customer_name", "Customer").split()
        masked_name = name_parts[0] if name_parts else "Customer"
        
        purchases.append({
            "name": masked_name,
            "location": random.choice(NEPAL_CITIES),
            "product": order.get("items_text", "Digital Product"),
            "time_ago": "Just now",
            "is_real": True
        })
    
    # If we don't have enough real orders, add simulated ones
    if len(purchases) < limit:
        # Get some products for simulation
        products = await db.products.find({"is_active": True}, {"_id": 0, "name": 1}).limit(20).to_list(20)
        product_names = [p["name"] for p in products] if products else ["Netflix Premium", "Spotify Premium", "YouTube Premium"]
        
        # Common Nepali first names
        names = ["Aarav", "Sita", "Ram", "Gita", "Bikash", "Anita", "Sunil", "Priya", "Rajesh", "Maya", "Dipak", "Sunita", "Anil", "Kamala", "Binod"]
        
        times_ago = ["2 min ago", "5 min ago", "8 min ago", "12 min ago", "15 min ago", "20 min ago", "25 min ago", "30 min ago"]
        
        while len(purchases) < limit:
            purchases.append({
                "name": random.choice(names),
                "location": random.choice(NEPAL_CITIES),
                "product": random.choice(product_names),
                "time_ago": random.choice(times_ago),
                "is_real": False
            })
    
    random.shuffle(purchases)
    return purchases[:limit]

# ==================== WISHLIST ====================

class WishlistItem(BaseModel):
    product_id: str
    variation_id: Optional[str] = None

class WishlistCreate(BaseModel):
    visitor_id: str  # Browser fingerprint or localStorage ID
    product_id: str
    variation_id: Optional[str] = None
    email: Optional[str] = None  # For price drop notifications

@api_router.get("/wishlist/{visitor_id}")
async def get_wishlist(visitor_id: str):
    """Get wishlist items for a visitor"""
    items = await db.wishlists.find({"visitor_id": visitor_id}, {"_id": 0}).to_list(100)
    
    # Populate product details
    for item in items:
        product = await db.products.find_one({"id": item.get("product_id")}, {"_id": 0})
        item["product"] = product
    
    return items

@api_router.post("/wishlist")
async def add_to_wishlist(data: WishlistCreate):
    """Add item to wishlist"""
    # Check if already in wishlist
    existing = await db.wishlists.find_one({
        "visitor_id": data.visitor_id,
        "product_id": data.product_id,
        "variation_id": data.variation_id
    })
    
    if existing:
        return {"message": "Already in wishlist", "id": existing.get("id")}
    
    # Get current price for tracking
    product = await db.products.find_one({"id": data.product_id})
    current_price = None
    if product and data.variation_id:
        for v in product.get("variations", []):
            if v.get("id") == data.variation_id:
                current_price = v.get("price")
                break
    elif product and product.get("variations"):
        current_price = product["variations"][0].get("price")
    
    wishlist_item = {
        "id": str(uuid.uuid4()),
        "visitor_id": data.visitor_id,
        "product_id": data.product_id,
        "variation_id": data.variation_id,
        "email": data.email,
        "price_when_added": current_price,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.wishlists.insert_one(wishlist_item)
    return {"message": "Added to wishlist", "id": wishlist_item["id"]}

@api_router.delete("/wishlist/{visitor_id}/{product_id}")
async def remove_from_wishlist(visitor_id: str, product_id: str, variation_id: Optional[str] = None):
    """Remove item from wishlist"""
    query = {"visitor_id": visitor_id, "product_id": product_id}
    if variation_id:
        query["variation_id"] = variation_id
    
    result = await db.wishlists.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    return {"message": "Removed from wishlist"}

@api_router.put("/wishlist/{visitor_id}/email")
async def update_wishlist_email(visitor_id: str, email: str):
    """Update email for price drop notifications"""
    await db.wishlists.update_many(
        {"visitor_id": visitor_id},
        {"$set": {"email": email}}
    )
    return {"message": "Email updated for notifications"}

# ==================== ORDER TRACKING ====================

class OrderStatusUpdate(BaseModel):
    status: str  # pending, processing, completed, cancelled
    note: Optional[str] = None

# ==================== NEWSLETTER ====================

class NewsletterSubscribe(BaseModel):
    email: str
    name: Optional[str] = None

@api_router.post("/newsletter/subscribe")
async def subscribe_newsletter(data: NewsletterSubscribe):
    """Subscribe to newsletter"""
    email = data.email.lower().strip()
    
    # Validate email format
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    # Check if already subscribed
    existing = await db.newsletter.find_one({"email": email})
    if existing:
        if existing.get("is_active", True):
            return {"message": "You're already subscribed!", "already_subscribed": True}
        else:
            # Reactivate subscription
            await db.newsletter.update_one(
                {"email": email},
                {"$set": {"is_active": True, "resubscribed_at": datetime.now(timezone.utc).isoformat()}}
            )
            return {"message": "Welcome back! You've been resubscribed.", "resubscribed": True}
    
    # Create new subscription
    subscriber = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": data.name,
        "is_active": True,
        "subscribed_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.newsletter.insert_one(subscriber)
    
    return {"message": "Successfully subscribed to our newsletter!", "success": True}

@api_router.post("/newsletter/unsubscribe")
async def unsubscribe_newsletter(email: str):
    """Unsubscribe from newsletter"""
    email = email.lower().strip()
    
    result = await db.newsletter.update_one(
        {"email": email},
        {"$set": {"is_active": False, "unsubscribed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Email not found in subscribers")
    
    return {"message": "Successfully unsubscribed"}

@api_router.get("/newsletter/subscribers")
async def get_newsletter_subscribers(current_user: dict = Depends(get_current_user)):
    """Get all newsletter subscribers (admin only)"""
    subscribers = await db.newsletter.find(
        {"is_active": True},
        {"_id": 0}
    ).sort("subscribed_at", -1).to_list(10000)
    
    return subscribers

@api_router.get("/newsletter/stats")
async def get_newsletter_stats(current_user: dict = Depends(get_current_user)):
    """Get newsletter statistics"""
    total = await db.newsletter.count_documents({})
    active = await db.newsletter.count_documents({"is_active": True})
    
    # Get subscribers in last 7 days
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent = await db.newsletter.count_documents({
        "subscribed_at": {"$gte": week_ago},
        "is_active": True
    })
    
    return {
        "total": total,
        "active": active,
        "unsubscribed": total - active,
        "recent_week": recent
    }

@api_router.get("/orders/track/{order_id}")
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

@api_router.put("/orders/{order_id}/status")
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
    
    credits_deducted = 0
    credits_awarded = 0
    customer_email = order.get("customer_email")
    
    # Deduct credits when order is CONFIRMED (not pending anymore)
    if new_status == "confirmed" and old_status.lower() != "confirmed":
        credits_used = order.get("credits_used", 0)
        if credits_used > 0 and customer_email and order.get("credits_pending"):
            try:
                await use_credits(customer_email, credits_used, order_id)
                credits_deducted = credits_used
                # Mark credits as deducted
                await db.orders.update_one(
                    {"id": order_id},
                    {"$set": {"credits_pending": False, "credits_deducted": True}}
                )
                logger.info(f"Deducted {credits_used} credits from {customer_email} for confirmed order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to deduct credits for order {order_id}: {e}")
    
    # Award credits when order is COMPLETED
    if new_status == "completed" and old_status.lower() != "completed":
        if customer_email:
            try:
                order_total = order.get("total_amount", 0)
                credit_result = await award_credits_for_order(order_id, customer_email, order_total)
                credits_awarded = credit_result.get("credits_awarded", 0)
                if credits_awarded > 0:
                    logger.info(f"Awarded {credits_awarded} credits to {customer_email} for completed order {order_id}")
            except Exception as e:
                logger.warning(f"Failed to award credits for order {order_id}: {e}")
    
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

@api_router.get("/orders/{order_id}")
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

# ==================== ANALYTICS DASHBOARD ====================

@api_router.get("/analytics/overview")
async def get_analytics_overview(current_user: dict = Depends(get_current_user)):
    """Get overview analytics for admin dashboard"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    
    # Calculate last month date range
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = (first_of_this_month - timedelta(days=1)).isoformat()
    last_month_start = first_of_this_month.replace(month=first_of_this_month.month - 1 if first_of_this_month.month > 1 else 12, 
                                                    year=first_of_this_month.year if first_of_this_month.month > 1 else first_of_this_month.year - 1).isoformat()
    
    # Today's stats
    today_orders = await db.orders.count_documents({"created_at": {"$gte": today_start}})
    today_revenue_cursor = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": today_start}, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    today_revenue = today_revenue_cursor[0]["total"] if today_revenue_cursor else 0
    
    # This week stats
    week_orders = await db.orders.count_documents({"created_at": {"$gte": week_ago}})
    week_revenue_cursor = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": week_ago}, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    week_revenue = week_revenue_cursor[0]["total"] if week_revenue_cursor else 0
    
    # This month stats
    month_orders = await db.orders.count_documents({"created_at": {"$gte": month_ago}})
    month_revenue_cursor = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": month_ago}, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    month_revenue = month_revenue_cursor[0]["total"] if month_revenue_cursor else 0
    
    # Last month stats
    last_month_orders = await db.orders.count_documents({
        "created_at": {"$gte": last_month_start, "$lte": last_month_end}
    })
    last_month_revenue_cursor = await db.orders.aggregate([
        {"$match": {"created_at": {"$gte": last_month_start, "$lte": last_month_end}, "status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    last_month_revenue = last_month_revenue_cursor[0]["total"] if last_month_revenue_cursor else 0
    
    # Total stats (all time)
    total_orders = await db.orders.count_documents({})
    total_revenue_cursor = await db.orders.aggregate([
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    total_revenue = total_revenue_cursor[0]["total"] if total_revenue_cursor else 0
    
    # Website visits
    today_visits = await db.visits.count_documents({"date": today_start[:10]})
    week_visits = await db.visits.count_documents({"created_at": {"$gte": week_ago}})
    month_visits = await db.visits.count_documents({"created_at": {"$gte": month_ago}})
    last_month_visits = await db.visits.count_documents({
        "created_at": {"$gte": last_month_start, "$lte": last_month_end}
    })
    total_visits = await db.visits.count_documents({})
    
    return {
        "today": {"orders": today_orders, "revenue": today_revenue},
        "week": {"orders": week_orders, "revenue": week_revenue},
        "month": {"orders": month_orders, "revenue": month_revenue},
        "lastMonth": {"orders": last_month_orders, "revenue": last_month_revenue},
        "total": {"orders": total_orders, "revenue": total_revenue},
        "visits": {
            "today": today_visits,
            "week": week_visits,
            "month": month_visits,
            "lastMonth": last_month_visits,
            "total": total_visits
        }
    }

@api_router.post("/track-visit")
async def track_visit(request: Request):
    """Track a website visit - called from frontend"""
    try:
        # Get visitor identifier from header or generate session-based
        visitor_id = request.headers.get("X-Visitor-ID", "")
        user_agent = request.headers.get("User-Agent", "")
        
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        
        # Only count unique visits per day per visitor
        existing = await db.visits.find_one({
            "visitor_id": visitor_id,
            "date": today
        })
        
        if not existing and visitor_id:
            await db.visits.insert_one({
                "visitor_id": visitor_id,
                "date": today,
                "user_agent": user_agent,
                "created_at": now.isoformat()
            })
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error tracking visit: {e}")
        return {"success": False}

@api_router.get("/analytics/top-products")
async def get_top_products(current_user: dict = Depends(get_current_user), limit: int = 10):
    """Get top selling products - only counts completed orders"""
    # Aggregate orders to find top products - only from completed orders
    pipeline = [
        {"$match": {"status": {"$in": ["completed", "Completed", "delivered"]}}},
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.name",
            "total_quantity": {"$sum": "$items.quantity"},
            "total_revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}}
        }},
        {"$sort": {"total_quantity": -1}},
        {"$limit": limit}
    ]
    
    top_products = await db.orders.aggregate(pipeline).to_list(limit)
    
    return [
        {
            "name": p["_id"],
            "quantity": p["total_quantity"],
            "revenue": p["total_revenue"]
        }
        for p in top_products
    ]

@api_router.get("/analytics/revenue-chart")
async def get_revenue_chart(current_user: dict = Depends(get_current_user), days: int = 30):
    """Get daily revenue for chart"""
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).isoformat()
    
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date}, "status": {"$ne": "cancelled"}}},
        {"$addFields": {
            "date": {"$substr": ["$created_at", 0, 10]}
        }},
        {"$group": {
            "_id": "$date",
            "orders": {"$sum": 1},
            "revenue": {"$sum": "$total_amount"}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_data = await db.orders.aggregate(pipeline).to_list(days)
    
    # Fill in missing dates with zero values
    result = []
    current = now - timedelta(days=days)
    data_map = {d["_id"]: d for d in daily_data}
    
    for i in range(days + 1):
        date_str = current.strftime("%Y-%m-%d")
        if date_str in data_map:
            result.append({
                "date": date_str,
                "orders": data_map[date_str]["orders"],
                "revenue": data_map[date_str]["revenue"]
            })
        else:
            result.append({"date": date_str, "orders": 0, "revenue": 0})
        current += timedelta(days=1)
    
    return result

@api_router.get("/analytics/order-status")
async def get_order_status_breakdown(current_user: dict = Depends(get_current_user)):
    """Get order status breakdown"""
    pipeline = [
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    status_data = await db.orders.aggregate(pipeline).to_list(10)
    
    return {
        item["_id"] or "pending": item["count"]
        for item in status_data
    }

@api_router.get("/analytics/profit")
async def get_profit_analytics(current_user: dict = Depends(get_current_user)):
    """Get profit analytics based on cost price vs selling price"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    
    # Calculate last month date range
    first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = (first_of_this_month - timedelta(days=1)).isoformat()
    last_month_start = first_of_this_month.replace(month=first_of_this_month.month - 1 if first_of_this_month.month > 1 else 12, 
                                                    year=first_of_this_month.year if first_of_this_month.month > 1 else first_of_this_month.year - 1).isoformat()
    
    # Get all completed orders (case-insensitive status check)
    all_orders = await db.orders.find({}).to_list(10000)
    completed_orders = [o for o in all_orders if (o.get("status", "").lower() in ["completed", "delivered"])]
    
    # Get all products to map cost prices
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    
    # Create variation cost price lookup
    cost_lookup = {}
    for product in products:
        for var in product.get("variations", []):
            key = f"{product['id']}_{var['id']}"
            cost_lookup[key] = var.get("cost_price", 0) or 0
    
    # Calculate profits
    def calculate_profit(orders):
        total_revenue = 0
        total_cost = 0
        for order in orders:
            total_revenue += order.get("total_amount", 0)
            for item in order.get("items", []):
                key = f"{item.get('product_id', '')}_{item.get('variation_id', '')}"
                cost = cost_lookup.get(key, 0)
                qty = item.get("quantity", 1)
                total_cost += cost * qty
        return {"revenue": total_revenue, "cost": total_cost, "profit": total_revenue - total_cost}
    
    # Filter orders by time periods
    today_orders = [o for o in completed_orders if o.get("created_at", "") >= today_start]
    week_orders = [o for o in completed_orders if o.get("created_at", "") >= week_ago]
    month_orders = [o for o in completed_orders if o.get("created_at", "") >= month_ago]
    last_month_orders = [o for o in completed_orders if last_month_start <= o.get("created_at", "") <= last_month_end]
    
    return {
        "today": calculate_profit(today_orders),
        "week": calculate_profit(week_orders),
        "month": calculate_profit(month_orders),
        "lastMonth": calculate_profit(last_month_orders),
        "total": calculate_profit(completed_orders),
        "all_time": calculate_profit(completed_orders)
    }

# ==================== GOOGLE SHEETS ====================

@api_router.get("/google-sheets/test")
async def test_google_sheets(current_user: dict = Depends(get_current_user)):
    """Test Google Sheets connection"""
    return google_sheets_service.test_connection()

@api_router.post("/google-sheets/sync-all")
async def sync_all_to_sheets(current_user: dict = Depends(get_current_user)):
    """Sync all customers and orders to Google Sheets"""
    # Sync all customers
    customers = await db.customers.find({}, {"_id": 0}).to_list(10000)
    customers_synced = 0
    for customer in customers:
        try:
            google_sheets_service.sync_customer_to_sheets(customer)
            customers_synced += 1
        except Exception as e:
            logger.error(f"Failed to sync customer {customer.get('email')}: {e}")
    
    # Sync all orders
    orders = await db.orders.find({}, {"_id": 0}).to_list(10000)
    orders_synced = 0
    for order in orders:
        try:
            google_sheets_service.sync_order_to_sheets(order)
            orders_synced += 1
        except Exception as e:
            logger.error(f"Failed to sync order {order.get('id')}: {e}")
    
    return {
        "success": True,
        "customers_synced": customers_synced,
        "orders_synced": orders_synced
    }

# ==================== SEO / SITEMAP ====================

from fastapi.responses import Response

@api_router.get("/sitemap.xml")
async def get_sitemap():
    """Generate dynamic sitemap for SEO"""
    base_url = os.environ.get("SITE_URL", "https://gameshopnepal.com")
    
    # Static pages
    static_pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/about", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/faq", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/terms", "priority": "0.5", "changefreq": "monthly"},
        {"loc": "/blog", "priority": "0.8", "changefreq": "weekly"},
    ]
    
    # Get all active products
    products = await db.products.find({"is_active": True}, {"slug": 1}).to_list(1000)
    
    # Get all published blog posts
    blog_posts = await db.blog_posts.find({"is_published": True}, {"slug": 1}).to_list(100)
    
    # Get all categories
    categories = await db.categories.find({}, {"slug": 1}).to_list(100)
    
    # Build sitemap XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Add static pages
    for page in static_pages:
        xml_content += f'''  <url>
    <loc>{base_url}{page["loc"]}</loc>
    <changefreq>{page["changefreq"]}</changefreq>
    <priority>{page["priority"]}</priority>
  </url>\n'''
    
    # Add products
    for product in products:
        if product.get("slug"):
            xml_content += f'''  <url>
    <loc>{base_url}/product/{product["slug"]}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>\n'''
    
    # Add blog posts
    for post in blog_posts:
        if post.get("slug"):
            xml_content += f'''  <url>
    <loc>{base_url}/blog/{post["slug"]}</loc>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>\n'''
    
    # Add categories
    for category in categories:
        if category.get("slug"):
            xml_content += f'''  <url>
    <loc>{base_url}/category/{category["slug"]}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>\n'''
    
    xml_content += '</urlset>'
    
    return Response(content=xml_content, media_type="application/xml")

@api_router.get("/seo/meta/{page_type}/{slug}")
async def get_seo_meta(page_type: str, slug: str):
    """Get SEO meta data for a specific page"""
    if page_type == "product":
        product = await db.products.find_one({"slug": slug}, {"_id": 0})
        if product:
            # Get lowest price from variations
            min_price = min([v.get("price", 0) for v in product.get("variations", [])]) if product.get("variations") else 0
            
            return {
                "title": f"{product['name']} - Buy Online | GameShop Nepal",
                "description": f"Buy {product['name']} at the best price in Nepal. Starting from Rs {min_price}. Instant delivery, 100% genuine products.",
                "keywords": f"{product['name']}, buy {product['name']} Nepal, {product['name']} price Nepal, digital products Nepal",
                "og_image": product.get("image_url"),
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "Product",
                    "name": product["name"],
                    "description": product.get("description", "")[:200].replace("<p>", "").replace("</p>", ""),
                    "image": product.get("image_url"),
                    "offers": {
                        "@type": "AggregateOffer",
                        "lowPrice": min_price,
                        "priceCurrency": "NPR",
                        "availability": "https://schema.org/InStock" if not product.get("is_sold_out") else "https://schema.org/OutOfStock"
                    }
                }
            }
    
    elif page_type == "blog":
        post = await db.blog_posts.find_one({"slug": slug}, {"_id": 0})
        if post:
            return {
                "title": f"{post['title']} | GameShop Nepal Blog",
                "description": post.get("excerpt", post.get("content", "")[:160]),
                "keywords": f"{post['title']}, gaming blog Nepal, digital products guide",
                "og_image": post.get("image_url"),
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "BlogPosting",
                    "headline": post["title"],
                    "description": post.get("excerpt", ""),
                    "image": post.get("image_url"),
                    "datePublished": post.get("created_at"),
                    "author": {"@type": "Organization", "name": "GameShop Nepal"}
                }
            }
    
    # Default meta
    return {
        "title": "GameShop Nepal - Digital Products at Best Prices",
        "description": "Buy Netflix, Spotify, YouTube Premium, PUBG UC and more at the best prices in Nepal. Instant delivery, 100% genuine products.",
        "keywords": "digital products Nepal, Netflix Nepal, Spotify Nepal, gaming topup Nepal"
    }

# ==================== CUSTOMER ACCOUNTS ====================

class CustomerLogin(BaseModel):
    phone: str
    otp: Optional[str] = None

class CustomerProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    
@api_router.post("/customers/login")
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
        
        return {
            "token": token,
            "customer": {
                "id": customer["id"],
                "phone": customer["phone"],
                "name": customer.get("name"),
                "email": customer.get("email")
            }
        }

@api_router.post("/customers/sync-from-takeapp")
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

@api_router.get("/customers")
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

# ==================== DAILY REWARDS ====================

class DailyRewardSettings(BaseModel):
    is_enabled: bool = True
    reward_amount: float = 10.0  # Credits to award daily
    streak_bonus_enabled: bool = True
    streak_milestones: dict = {
        "7": 50,   # 7 day streak bonus
        "30": 200  # 30 day streak bonus
    }

def get_nepal_date():
    """Get current date in Nepal timezone (UTC+5:45)"""
    nepal_offset = timedelta(hours=5, minutes=45)
    nepal_time = datetime.now(timezone.utc) + nepal_offset
    return nepal_time.date().isoformat()

def get_nepal_datetime():
    """Get current datetime in Nepal timezone (UTC+5:45)"""
    nepal_offset = timedelta(hours=5, minutes=45)
    return datetime.now(timezone.utc) + nepal_offset

async def get_active_multiplier_value(event_type: str = None) -> float:
    """Get the current active multiplier value"""
    now = datetime.now(timezone.utc).isoformat()
    
    query = {
        "is_active": True,
        "start_time": {"$lte": now},
        "end_time": {"$gte": now}
    }
    
    events = await db.multiplier_events.find(query).to_list(10)
    
    max_multiplier = 1.0
    for event in events:
        applies_to = event.get("applies_to", ["daily_reward", "cashback", "referral"])
        if event_type is None or event_type in applies_to:
            if event.get("multiplier", 1) > max_multiplier:
                max_multiplier = event.get("multiplier", 1)
    
    return max_multiplier

@api_router.get("/daily-reward/settings")
async def get_daily_reward_settings():
    """Get daily reward settings (public)"""
    settings = await db.daily_reward_settings.find_one({"id": "main"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "main",
            "is_enabled": True,
            "reward_amount": 10.0,
            "streak_bonus_enabled": True,
            "streak_milestones": {"7": 50, "30": 200}
        }
    return settings

@api_router.put("/daily-reward/settings")
async def update_daily_reward_settings(settings: DailyRewardSettings, current_user: dict = Depends(get_current_user)):
    """Update daily reward settings (admin only)"""
    settings_dict = settings.model_dump()
    settings_dict["id"] = "main"
    await db.daily_reward_settings.update_one({"id": "main"}, {"$set": settings_dict}, upsert=True)
    return settings_dict

@api_router.get("/daily-reward/status")
async def get_daily_reward_status(email: str):
    """Check if customer can claim daily reward and their streak"""
    settings = await db.daily_reward_settings.find_one({"id": "main"})
    if not settings:
        settings = {
            "is_enabled": True,
            "reward_amount": 10.0,
            "streak_bonus_enabled": True,
            "streak_milestones": {"7": 50, "30": 200}
        }
    
    if not settings.get("is_enabled", True):
        return {"can_claim": False, "reason": "Daily rewards are disabled", "streak": 0}
    
    customer = await db.customers.find_one({"email": email})
    if not customer:
        return {"can_claim": False, "reason": "Customer not found", "streak": 0}
    
    today = get_nepal_date()
    last_claim_date = customer.get("last_daily_reward_date")
    current_streak = customer.get("daily_reward_streak", 0)
    
    # Check if already claimed today
    if last_claim_date == today:
        return {
            "can_claim": False, 
            "reason": "Already claimed today", 
            "streak": current_streak,
            "last_claim": last_claim_date,
            "reward_amount": settings.get("reward_amount", 10),
            "next_reset": get_nepal_date()  # Resets at 12 AM Nepal time
        }
    
    # Check if streak should be reset (missed a day)
    if last_claim_date:
        yesterday = (get_nepal_datetime() - timedelta(days=1)).date().isoformat()
        if last_claim_date != yesterday:
            current_streak = 0  # Reset streak if missed a day
    
    return {
        "can_claim": True,
        "streak": current_streak,
        "next_streak": current_streak + 1,
        "reward_amount": settings.get("reward_amount", 10),
        "streak_bonus_enabled": settings.get("streak_bonus_enabled", True),
        "streak_milestones": settings.get("streak_milestones", {"7": 50, "30": 200}),
        "last_claim": last_claim_date
    }

@api_router.post("/daily-reward/claim")
async def claim_daily_reward(email: str):
    """Claim daily login reward"""
    settings = await db.daily_reward_settings.find_one({"id": "main"})
    if not settings or not settings.get("is_enabled", True):
        raise HTTPException(status_code=400, detail="Daily rewards are disabled")
    
    customer = await db.customers.find_one({"email": email})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    today = get_nepal_date()
    last_claim_date = customer.get("last_daily_reward_date")
    
    # Check if already claimed today
    if last_claim_date == today:
        raise HTTPException(status_code=400, detail="Already claimed today")
    
    # Calculate streak
    current_streak = customer.get("daily_reward_streak", 0)
    if last_claim_date:
        yesterday = (get_nepal_datetime() - timedelta(days=1)).date().isoformat()
        if last_claim_date == yesterday:
            current_streak += 1  # Continue streak
        else:
            current_streak = 1  # Reset streak
    else:
        current_streak = 1  # First claim
    
    # Calculate reward
    base_reward = settings.get("reward_amount", 10)
    streak_bonus = 0
    streak_milestone_reached = None
    
    # Check for streak milestones
    if settings.get("streak_bonus_enabled", True):
        milestones = settings.get("streak_milestones", {"7": 50, "30": 200})
        for days, bonus in milestones.items():
            if current_streak == int(days):
                streak_bonus = bonus
                streak_milestone_reached = int(days)
                break
    
    # Apply multiplier
    multiplier = await get_active_multiplier_value("daily_reward")
    base_reward_multiplied = base_reward * multiplier
    streak_bonus_multiplied = streak_bonus * multiplier
    total_reward = base_reward_multiplied + streak_bonus_multiplied
    
    # Update customer
    current_balance = customer.get("credit_balance", 0)
    new_balance = current_balance + total_reward
    
    await db.customers.update_one(
        {"email": email},
        {"$set": {
            "credit_balance": new_balance,
            "last_daily_reward_date": today,
            "daily_reward_streak": current_streak
        }}
    )
    
    # Log the credit transaction
    multiplier_text = f" ({multiplier}x multiplier!)" if multiplier > 1 else ""
    credit_log = {
        "id": str(uuid.uuid4()),
        "customer_id": customer.get("id"),
        "customer_email": email,
        "amount": total_reward,
        "reason": f"Daily login reward (Day {current_streak})" + (f" + {streak_milestone_reached}-day streak bonus!" if streak_bonus > 0 else "") + multiplier_text,
        "balance_before": current_balance,
        "balance_after": new_balance,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "type": "daily_reward",
        "multiplier": multiplier
    }
    await db.credit_logs.insert_one(credit_log)
    
    return {
        "success": True,
        "base_reward": base_reward_multiplied,
        "streak_bonus": streak_bonus_multiplied,
        "total_reward": total_reward,
        "new_balance": new_balance,
        "streak": current_streak,
        "streak_milestone_reached": streak_milestone_reached,
        "multiplier": multiplier,
        "message": f"You earned Rs {total_reward} credits!" + (f" 🎉 {streak_milestone_reached}-day streak bonus!" if streak_bonus > 0 else "") + (f" 🔥 {multiplier}x multiplier active!" if multiplier > 1 else "")
    }

# ==================== REFERRAL PROGRAM ====================

def generate_referral_code(length=8):
    """Generate a unique referral code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

class ReferralSettings(BaseModel):
    is_enabled: bool = True
    referrer_reward: float = 50.0  # Credits for person who refers
    referee_reward: float = 25.0   # Credits for new user who uses code
    min_purchase_required: bool = False  # Require purchase to earn referral bonus
    min_purchase_amount: float = 0

@api_router.get("/referral/settings")
async def get_referral_settings():
    """Get referral program settings"""
    settings = await db.referral_settings.find_one({"id": "main"}, {"_id": 0})
    if not settings:
        settings = {
            "id": "main",
            "is_enabled": True,
            "referrer_reward": 50.0,
            "referee_reward": 25.0,
            "min_purchase_required": False,
            "min_purchase_amount": 0
        }
    return settings

@api_router.put("/referral/settings")
async def update_referral_settings(settings: ReferralSettings, current_user: dict = Depends(get_current_user)):
    """Update referral settings (admin only)"""
    settings_dict = settings.model_dump()
    settings_dict["id"] = "main"
    await db.referral_settings.update_one({"id": "main"}, {"$set": settings_dict}, upsert=True)
    return settings_dict

@api_router.get("/referral/code/{email}")
async def get_referral_code(email: str):
    """Get or generate referral code for a customer"""
    customer = await db.customers.find_one({"email": email.lower()})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Check if customer already has a referral code
    referral_code = customer.get("referral_code")
    if not referral_code:
        # Generate unique code
        while True:
            referral_code = generate_referral_code()
            existing = await db.customers.find_one({"referral_code": referral_code})
            if not existing:
                break
        
        await db.customers.update_one(
            {"email": email.lower()},
            {"$set": {"referral_code": referral_code}}
        )
    
    # Get referral stats
    referral_count = await db.referrals.count_documents({"referrer_email": email.lower()})
    total_earned = 0
    referrals = await db.referrals.find({"referrer_email": email.lower()}).to_list(100)
    for ref in referrals:
        total_earned += ref.get("referrer_reward", 0)
    
    # Check if user has already used a referral code
    has_used_referral = customer.get("referred_by") is not None
    
    return {
        "referral_code": referral_code,
        "referral_count": referral_count,
        "total_earned": total_earned,
        "has_used_referral": has_used_referral
    }

@api_router.post("/referral/apply")
async def apply_referral_code(referee_email: str, referral_code: str):
    """Apply a referral code for a new user"""
    settings = await db.referral_settings.find_one({"id": "main"})
    if not settings or not settings.get("is_enabled", True):
        raise HTTPException(status_code=400, detail="Referral program is currently disabled")
    
    # Find referrer by code
    referrer = await db.customers.find_one({"referral_code": referral_code.upper()})
    if not referrer:
        raise HTTPException(status_code=400, detail="Invalid referral code")
    
    # Check if referee exists
    referee = await db.customers.find_one({"email": referee_email.lower()})
    if not referee:
        raise HTTPException(status_code=404, detail="Your account not found")
    
    # Check if same person
    if referrer["email"].lower() == referee_email.lower():
        raise HTTPException(status_code=400, detail="You cannot use your own referral code")
    
    # Check if already used a referral code
    if referee.get("referred_by"):
        raise HTTPException(status_code=400, detail="You have already used a referral code")
    
    # Check if referee already has purchases (not a new user)
    order_count = await db.orders.count_documents({"customer_email": referee_email.lower()})
    if order_count > 0:
        raise HTTPException(status_code=400, detail="Referral codes are only for new users")
    
    referee_reward = settings.get("referee_reward", 25)
    referrer_reward = settings.get("referrer_reward", 50)
    
    # Get active multiplier
    multiplier = await get_active_multiplier_value("referral")
    referee_reward = referee_reward * multiplier
    referrer_reward = referrer_reward * multiplier
    
    # Award credits to referee immediately
    referee_balance = referee.get("credit_balance", 0)
    await db.customers.update_one(
        {"email": referee_email.lower()},
        {"$set": {
            "credit_balance": referee_balance + referee_reward,
            "referred_by": referrer["email"],
            "referred_by_code": referral_code.upper()
        }}
    )
    
    # Log credit for referee
    await db.credit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "customer_email": referee_email.lower(),
        "amount": referee_reward,
        "reason": f"Welcome bonus - used referral code {referral_code.upper()}" + (f" ({multiplier}x multiplier)" if multiplier > 1 else ""),
        "type": "referral_bonus",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Award credits to referrer (can be immediate or after first purchase based on settings)
    if not settings.get("min_purchase_required", False):
        referrer_balance = referrer.get("credit_balance", 0)
        await db.customers.update_one(
            {"email": referrer["email"]},
            {"$set": {"credit_balance": referrer_balance + referrer_reward}}
        )
        
        await db.credit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "customer_email": referrer["email"],
            "amount": referrer_reward,
            "reason": f"Referral bonus - {referee_email} joined" + (f" ({multiplier}x multiplier)" if multiplier > 1 else ""),
            "type": "referral_reward",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        referrer_credited = True
    else:
        referrer_credited = False
    
    # Record the referral
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()),
        "referrer_email": referrer["email"],
        "referee_email": referee_email.lower(),
        "referral_code": referral_code.upper(),
        "referee_reward": referee_reward,
        "referrer_reward": referrer_reward if referrer_credited else 0,
        "referrer_pending_reward": 0 if referrer_credited else referrer_reward,
        "referrer_credited": referrer_credited,
        "multiplier_applied": multiplier,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"Referral code applied! You received Rs {referee_reward} credits!",
        "credits_received": referee_reward,
        "multiplier": multiplier
    }

@api_router.get("/referral/history/{email}")
async def get_referral_history(email: str):
    """Get referral history for a customer"""
    referrals = await db.referrals.find({"referrer_email": email.lower()}).sort("created_at", -1).to_list(100)
    for ref in referrals:
        ref["id"] = str(ref.get("_id", ref.get("id")))
        if "_id" in ref:
            del ref["_id"]
    return referrals

@api_router.get("/referrals/all")
async def get_all_referrals(current_user: dict = Depends(get_current_user)):
    """Get all referrals for admin panel"""
    referrals = await db.referrals.find().sort("created_at", -1).to_list(100)
    for ref in referrals:
        ref["id"] = str(ref.get("_id", ref.get("id")))
        if "_id" in ref:
            del ref["_id"]
    return referrals

# ==================== POINTS MULTIPLIER EVENTS ====================

class MultiplierEvent(BaseModel):
    name: str
    multiplier: float = 2.0
    start_time: str  # ISO format datetime
    end_time: str    # ISO format datetime
    applies_to: List[str] = ["daily_reward", "cashback", "referral"]  # What it applies to
    is_active: bool = True

@api_router.get("/multiplier/active")
async def get_active_multiplier_event():
    """Get current active multiplier event (public)"""
    now = datetime.now(timezone.utc).isoformat()
    
    event = await db.multiplier_events.find_one({
        "is_active": True,
        "start_time": {"$lte": now},
        "end_time": {"$gte": now}
    }, {"_id": 0})
    
    if event:
        return {
            "is_active": True,
            "name": event.get("name"),
            "multiplier": event.get("multiplier", 2),
            "end_time": event.get("end_time"),
            "applies_to": event.get("applies_to", ["daily_reward", "cashback", "referral"])
        }
    
    return {"is_active": False, "multiplier": 1}

@api_router.get("/multiplier/events")
async def get_multiplier_events(current_user: dict = Depends(get_current_user)):
    """Get all multiplier events (admin only)"""
    events = await db.multiplier_events.find().sort("start_time", -1).to_list(100)
    for event in events:
        event["id"] = str(event.get("_id", event.get("id")))
        if "_id" in event:
            del event["_id"]
    return events

@api_router.post("/multiplier/events")
async def create_multiplier_event(event: MultiplierEvent, current_user: dict = Depends(get_current_user)):
    """Create a new multiplier event (admin only)"""
    event_dict = event.model_dump()
    event_dict["id"] = str(uuid.uuid4())
    event_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.multiplier_events.insert_one(event_dict)
    # Remove MongoDB's _id from response
    if "_id" in event_dict:
        del event_dict["_id"]
    return event_dict

@api_router.put("/multiplier/events/{event_id}")
async def update_multiplier_event(event_id: str, event: MultiplierEvent, current_user: dict = Depends(get_current_user)):
    """Update a multiplier event (admin only)"""
    result = await db.multiplier_events.update_one(
        {"id": event_id},
        {"$set": event.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event updated"}

@api_router.delete("/multiplier/events/{event_id}")
async def delete_multiplier_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a multiplier event (admin only)"""
    result = await db.multiplier_events.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}

# ==================== NEWSLETTER ====================

from newsletter_service import get_template_list, render_template, send_newsletter, NEWSLETTER_TEMPLATES

class NewsletterSendRequest(BaseModel):
    template_id: str
    variables: dict
    recipient_filter: str = "all"  # all, subscribed, recent_buyers
    test_email: Optional[str] = None  # For test sends

@api_router.get("/newsletter/templates")
async def get_newsletter_templates(current_user: dict = Depends(get_current_user)):
    """Get available newsletter templates"""
    return get_template_list()

@api_router.post("/newsletter/preview")
async def preview_newsletter(request: NewsletterSendRequest, current_user: dict = Depends(get_current_user)):
    """Preview a newsletter before sending"""
    try:
        subject, html = render_template(request.template_id, request.variables)
        return {"subject": subject, "html": html}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/newsletter/send-test")
async def send_test_newsletter(request: NewsletterSendRequest, current_user: dict = Depends(get_current_user)):
    """Send test newsletter to a single email"""
    if not request.test_email:
        raise HTTPException(status_code=400, detail="Test email required")
    
    try:
        subject, html = render_template(request.template_id, request.variables)
        result = send_newsletter([request.test_email], subject, html)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.post("/newsletter/send")
async def send_bulk_newsletter(request: NewsletterSendRequest, current_user: dict = Depends(get_current_user)):
    """Send newsletter to customers based on filter"""
    try:
        subject, html = render_template(request.template_id, request.variables)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get recipients based on filter
    query = {}
    if request.recipient_filter == "subscribed":
        query["newsletter_subscribed"] = {"$ne": False}
    elif request.recipient_filter == "recent_buyers":
        # Customers who ordered in last 30 days
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        recent_orders = await db.orders.distinct("customer_email", {
            "created_at": {"$gte": thirty_days_ago}
        })
        query["email"] = {"$in": [e for e in recent_orders if e]}
    
    customers = await db.customers.find(query, {"email": 1, "_id": 0}).to_list(10000)
    emails = [c["email"] for c in customers if c.get("email")]
    
    if not emails:
        raise HTTPException(status_code=400, detail="No recipients found")
    
    # Send newsletter
    result = send_newsletter(emails, subject, html)
    
    # Log the campaign
    campaign_log = {
        "id": str(uuid.uuid4()),
        "template_id": request.template_id,
        "subject": subject,
        "recipient_filter": request.recipient_filter,
        "total_recipients": len(emails),
        "sent": result.get("sent", 0),
        "failed": result.get("failed", 0),
        "sent_by": current_user.get("username"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.newsletter_campaigns.insert_one(campaign_log)
    
    return {
        "success": result.get("success", False),
        "total_recipients": len(emails),
        "sent": result.get("sent", 0),
        "failed": result.get("failed", 0),
        "campaign_id": campaign_log["id"]
    }

@api_router.get("/newsletter/campaigns")
async def get_newsletter_campaigns(current_user: dict = Depends(get_current_user)):
    """Get newsletter campaign history"""
    campaigns = await db.newsletter_campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return campaigns

@api_router.get("/newsletter/subscribers/count")
async def get_subscriber_count(current_user: dict = Depends(get_current_user)):
    """Get subscriber counts for different filters"""
    total = await db.customers.count_documents({"email": {"$exists": True, "$ne": None}})
    subscribed = await db.customers.count_documents({"newsletter_subscribed": {"$ne": False}, "email": {"$exists": True}})
    
    # Recent buyers (last 30 days)
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent_emails = await db.orders.distinct("customer_email", {"created_at": {"$gte": thirty_days_ago}})
    recent_buyers = len([e for e in recent_emails if e])
    
    return {
        "all": total,
        "subscribed": subscribed,
        "recent_buyers": recent_buyers
    }

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "GameShop Nepal API"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    asyncio.create_task(run_cleanup_task())
    logger.info("✅ Order cleanup task started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
