# GameShop Nepal (GSN) - Digital Products E-commerce

## Original Problem Statement
Build a premium, modern, dark-themed e-commerce website for digital goods, inspired by ottsathi.com and gameshopnepal.com.

## Current Repository
**Source:** https://github.com/gamerbolte/Nobeosh (swapped on Feb 18, 2026)

## Admin Access
- **URL:** `/panelgsnadminbackend/login`
- **Username/Email:** `gsnadmin`
- **Password:** `gsnadmin`

## Core Features Implemented
- Homepage with customer reviews and product grid
- Product system with variations (different plans/prices) with stock management
- Checkout & payment flow with HEIC/HEIF support
- Admin panel for managing products, categories, reviews, blogs, FAQs, orders
- Customer OTP-based login + Direct Google OAuth with profile completion flow
- Daily rewards system
- Referral program
- Store credits system with category eligibility and max usage per order
- Newsletter management with color customization
- Promo codes
- AI Chatbot powered by ChatGPT
- Liquid glass UI design with orange brand theme
- PWA support (Add to Home Screen) for admin panel
- Discord order notifications via webhook
- Self-hosted ad management system
- Product variation stock tracking
- Advanced customer management (sorting, ranking badges)
- **On-Site Review System** - Native customer reviews with approval workflow (replaced Trustpilot)

## Technical Stack
- **Backend:** FastAPI, Python, Motor (async MongoDB), APScheduler
- **Frontend:** React, Tailwind CSS, Shadcn UI, Recharts
- **Database:** MongoDB
- **Image Processing:** Pillow, pillow-heif (HEIC conversion)
- **Auth:** JWT (Admin), Email OTP + JWT (Customer), Direct Google OAuth

## Database Collections
- admins, customers, products, categories, orders
- reviews (now with status, customer_id, is_customer_review fields), faqs, blog_posts, pages
- payment_methods, promo_codes, social_links
- notification_bar, site_settings, trustpilot_config
- visits, users, otp_records, newsletter
- bundles, order_status_history, takeapp_orders, permissions

## Environment Variables
### Backend (.env)
- MONGO_URL, DB_NAME
- ADMIN_USERNAME, ADMIN_PASSWORD
- JWT_SECRET
- IMGBB_API_KEY
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_FROM_NAME
- GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
- DISCORD_ORDER_WEBHOOK
- OPENAI_API_KEY, EMERGENT_LLM_KEY

### Frontend (.env)
- REACT_APP_BACKEND_URL
- REACT_APP_GOOGLE_CLIENT_ID

## API Prefix
All backend endpoints use `/api` prefix

## Key Review System Endpoints
- `GET /api/reviews` - Approved reviews for homepage (max 20)
- `GET /api/reviews/public?page=N` - Paginated public reviews with stats
- `GET /api/reviews/admin` - All reviews for admin (requires auth)
- `POST /api/reviews` - Admin creates manual review (auto-approved)
- `POST /api/reviews/customer` - Customer submits review (requires auth + completed order)
- `PUT /api/reviews/customer` - Customer updates their review
- `GET /api/reviews/my-review` - Customer's own review + eligibility
- `PUT /api/reviews/{id}/status?status=approved|rejected|pending` - Admin approval

## Changelog
- **Mar 14, 2026:** Implemented On-Site Review System:
  - Public `/reviews` page with rating stats, distribution chart, paginated reviews
  - Customer review submission (requires completed order, pending admin approval)
  - Admin review management with filter tabs (all/pending/approved/rejected/customer)
  - Admin can approve/reject customer reviews
  - Replaced all Trustpilot references on homepage and navbar
  - Homepage now shows dynamic avg rating and links to /reviews
  - Navbar has "Reviews" link with star icon
- **Mar 11, 2026:** Redesigned Admin Dashboard, completed Admin Experience Enhancements
- **Mar 9, 2026:** PWA admin, Discord webhook fix, stock per variation, Google login profile completion
- **Mar 3, 2026:** Self-hosted ad management system verified
- **Mar 1, 2026:** Fixed customer account 401 error, enhanced email templates
- **Feb 28, 2026:** AI chatbot, enhanced store credits, liquid glass UI
- **Feb 18, 2026:** Swapped to Nobeosh repository

## Pending/Future Tasks
### P0 - Critical
- **Refactor backend/server.py** (>6000 lines monolith -> modular APIRouter files)

### P1 - High Priority
- Reorder Product Variations (drag-and-drop in admin)
- Re-implement Product Variation Editing in Admin Panel
- Enhance FAQ Page with categories and search

### P2 - Medium Priority
- Flash Sales Timer (countdown for deals)
- Product Bundles (combo deals)
- Live purchase ticker
- Bundle deals section
- Loyalty/Rewards program enhancements

### P3 - Backlog
- eSewa/Khalti payment gateway integration
- Public Order Tracking Page improvements
- Take.app integrations
- Public referral program
- Help Center/Knowledge Base
