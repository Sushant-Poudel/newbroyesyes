# GameShop Nepal - Product Requirements Document

## Overview
A premium, dark-themed e-commerce website for digital goods, built with React (frontend) and FastAPI + MongoDB (backend).

## Tech Stack
- **Frontend**: React, Tailwind CSS, Shadcn/UI, Recharts, Sonner
- **Backend**: FastAPI, Motor (async MongoDB), Pydantic
- **Database**: MongoDB
- **Auth**: JWT tokens (admin + customer), Google OAuth (customer)
- **Integrations**: Discord webhooks, ImgBB image hosting, Google Sheets

## Architecture (Post-Refactor - March 2026)
```
/app/backend/
├── server.py              # Slim app orchestrator (160 lines)
├── database.py            # DB connection, JWT/Discord config
├── dependencies.py        # Auth deps, audit logging
├── utils.py               # Shared utility functions
├── routes/
│   ├── auth.py            # Admin auth + admin management
│   ├── customers.py       # Customer auth, OTP, Google OAuth, profiles
│   ├── products.py        # Products + categories + image upload
│   ├── orders.py          # Orders, payments, completion, tracking
│   ├── reviews.py         # Reviews + trustpilot + FAQs
│   ├── ads.py             # Ad management + tracking
│   ├── content.py         # Blog, pages, social links, settings
│   ├── promotions.py      # Promo codes + store credits + bundles
│   ├── analytics.py       # Analytics dashboard + audit logs
│   ├── engagement.py      # Rewards, referral, newsletter, wishlist
│   └── chatbot.py         # Chatbot, reseller plans, SEO
├── models/schemas.py
├── email_service.py
├── discord_service.py
├── imgbb_service.py
├── order_cleanup.py
├── daily_summary_service.py
└── google_sheets_service.py
```

## Implemented Features (Complete)
- Homepage with product grid, customer reviews, ads
- Product pages with variations, custom fields
- Multi-step checkout with WhatsApp redirect
- Payment screenshot upload (ImgBB)
- Admin panel (products, orders, reviews, analytics, etc.)
- Customer auth (OTP + Google OAuth)
- Promo codes, store credits, bundle deals
- Review system (on-site, customer reviews, rewards)
- Discord notifications for orders
- Ad management system
- Reseller plans page
- Newsletter system
- Daily rewards + referral program
- Blog, FAQ, static pages
- PWA support
- Sound notifications for new orders (admin)
- **Downloadable review images** (admin) - Canvas-based, layout: GSN logo top (black bg), rating badge, review quote (white bg), stars + name, GameShop Nepal branding bottom (black bg)
- Bottom tab bar (mobile) + dynamic island nav (desktop)
- **Backend refactored** from 6344-line monolith to 11 modular route files

## Prioritized Backlog

### P0 - Active/Recently Fixed
- ~~Navbar PWA icon on desktop~~ (FIXED - Apr 2026)
- ~~Account not showing after login~~ (FIXED - Apr 2026)

### P1 - High Priority
- Reorder product variations (drag-and-drop in admin)
- Enhanced FAQ with categories and search

### P2 - Medium Priority
- Flash sales timer (countdown for deals)
- Product bundles (combo deals)
- Live purchase ticker

### P3 - Future
- eSewa/Khalti payment gateway
- Public order tracking page
- Take.app integration
- Help Center / Knowledge Base
- Loyalty/rewards & referral enhancements
