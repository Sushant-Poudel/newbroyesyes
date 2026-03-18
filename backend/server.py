"""GameShop Nepal - Main Application Server"""
from fastapi import FastAPI, APIRouter, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="GameShop Nepal API", version="2.0.0")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ==================== API ROUTER + ROUTE REGISTRATION ====================

api_router = APIRouter()

# Import and include all route modules
from routes.auth import router as auth_router
from routes.products import router as products_router
from routes.orders import router as orders_router
from routes.reviews import router as reviews_router
from routes.ads import router as ads_router
from routes.content import router as content_router
from routes.promotions import router as promotions_router
from routes.analytics import router as analytics_router
from routes.engagement import router as engagement_router
from routes.chatbot import router as chatbot_router
from routes.customers import router as customers_router

api_router.include_router(auth_router)
api_router.include_router(products_router)
api_router.include_router(orders_router)
api_router.include_router(reviews_router)
api_router.include_router(ads_router)
api_router.include_router(content_router)
api_router.include_router(promotions_router)
api_router.include_router(analytics_router)
api_router.include_router(engagement_router)
api_router.include_router(chatbot_router)
api_router.include_router(customers_router)


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    from database import db
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

@api_router.get("/health")
async def api_health():
    from database import db
    try:
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


# ==================== ROOT ====================

@api_router.get("/")
async def root():
    from database import db
    products_count = await db.products.count_documents({})
    categories_count = await db.categories.count_documents({})
    orders_count = await db.orders.count_documents({})
    return {
        "name": "GameShop Nepal API",
        "version": "2.0.0",
        "status": "running",
        "stats": {
            "products": products_count,
            "categories": categories_count,
            "orders": orders_count
        }
    }


# ==================== STATIC FILE SERVING ====================

UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    file_path = UPLOADS_DIR / filename
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


# Mount API router
app.include_router(api_router, prefix="/api")


# ==================== STARTUP / SHUTDOWN ====================

@app.on_event("startup")
async def startup_db_client():
    from database import db
    try:
        await db.command("ping")
        logger.info("Connected to MongoDB successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

    # Start background tasks
    try:
        import asyncio
        from order_cleanup import run_cleanup_task
        asyncio.create_task(run_cleanup_task())
    except Exception as e:
        logger.warning(f"Failed to start cleanup task: {e}")
    
    try:
        from daily_summary_service import run_daily_summary_scheduler
        admin_email = os.environ.get("DAILY_SUMMARY_EMAIL", "")
        if admin_email:
            asyncio.create_task(run_daily_summary_scheduler(db, admin_email))
    except Exception as e:
        logger.warning(f"Failed to start daily summary scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    from database import client
    client.close()
    logger.info("MongoDB connection closed")
