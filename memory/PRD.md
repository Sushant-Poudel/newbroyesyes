# GameShop Nepal (GSN) - Digital Products E-commerce

## Original Problem Statement
Build a premium, modern, dark-themed e-commerce website for digital goods, inspired by ottsathi.com and gameshopnepal.com.

## Current Repository
**Source:** https://github.com/gamerbolte/Nobeosh (swapped on Feb 18, 2026)

## Admin Access
- **URL:** `/panelgsnadminbackend/login`
- **Username:** `gsnadmin`
- **Password:** `gsnadmin`

## Core Features Implemented
- Homepage with customer reviews and product grid
- Product system with variations (different plans/prices)
- Checkout & payment flow
- Admin panel for managing products, categories, reviews, blogs, FAQs, orders
- Customer OTP-based login system
- Daily rewards system
- Referral program
- Store credits system with category eligibility and max usage per order
- Newsletter management
- Promo codes
- AI Chatbot powered by ChatGPT
- Liquid glass UI design with orange brand theme

## Technical Stack
- **Backend:** FastAPI, Python, Motor (async MongoDB)
- **Frontend:** React, Tailwind CSS, Shadcn UI
- **Database:** MongoDB

## Database Collections (23 total)
- admins, customers, products, categories, orders
- reviews, faqs, blog_posts, pages
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
- TAKEAPP_API_KEY (optional)

### Frontend (.env)
- REACT_APP_BACKEND_URL

## API Prefix
All backend endpoints use `/api` prefix

## Changelog
- **Mar 1, 2026:** Fixed "couldn't fetch data" bug on Customer Account Page - added proper 401 error handling to redirect expired sessions to login
- **Mar 1, 2026:** Enhanced email templates with premium modern design, better visual hierarchy, and brand consistency
- **Feb 28, 2026:** Implemented AI chatbot with ChatGPT integration, enhanced store credit system
- **Feb 28, 2026:** Applied liquid glass UI redesign with orange brand theme
- **Feb 18, 2026:** Swapped to Nobeosh repository, preserved all data
- **Feb 15, 2026:** Fixed "Admin not found" bug in staff management (id vs _id issue)
- Multiple previous codebase swaps (gangbro, nglbro, ganguli, ganbro)

## Completed This Session
- ✅ Fixed customer account page 401 error handling (session expiry now properly redirects to login)
- ✅ Redesigned email templates with premium modern design

## Completed in Current Fork (Mar 9, 2026)
- ✅ **PWA "Add to Home Screen" in Admin Panel** - Added install instructions modal to admin panel mobile menu
- ✅ **Discord Webhook Management on Product Edit Page** - Status indicator, test button, add/remove URLs
- ✅ **Fixed Discord Webhooks Not Showing** - Created `/api/admin/products` endpoint
- ✅ **Stock per Variation** - Added stock tracking per variation with admin UI
- ✅ **Fixed Navbar Proportion Issue** - Fixed button overflow on mobile
- ✅ **Google Login Profile Completion** - Users must provide name & WhatsApp after Google OAuth
- ✅ **Sidebar Ads on Homepage** - Added `home_sidebar` ad position display in All Products section (XL screens)
- ✅ **Variation Stock Display on Product Page** - Shows stock per variation:
  - "Only X left!" in amber for low stock (1-5)
  - "X in stock" in green for normal stock
  - No indicator for unlimited (stock = 0)
  - Disabled selection for out of stock variations
- ✅ **Removed Dead Google OAuth Code** - Deleted AuthCallback.jsx and old Emergent Auth backend endpoint
- ✅ **Removed "About" from navbar** and **Made Reseller discount % optional**

## Completed in Previous Fork (Mar 3, 2026)
- ✅ Verified Self-Hosted Ad Management System - fully functional with:
  - Recommended image sizes displayed for all ad positions (Homepage Banner, Sidebar, Product Inline, Footer, Popup)
  - Preview button with Desktop/Mobile toggle and website context simulation
  - Stats dashboard (Total Ads, Active, Impressions, Clicks, CTR)
  - Position-based aspect ratio guidance
- ✅ Moved "Advertisements" menu from Content to Marketing section for better discoverability
- ✅ Ad positions available: home_banner (1200x200), home_sidebar (300x250), product_inline (728x90), product_page_sidebar (300x600), footer (970x90), popup (500x500)

## Pending/Future Tasks
### P1 - High Priority
- Re-implement Product Variation Editing in Admin Panel (edit/reorder variations)
- Enhance FAQ Page with categories and search

### P2 - Medium Priority
- Live purchase ticker
- Bundle deals section
- Loyalty/Rewards program enhancements
- Add sidebar ad component to homepage (home_sidebar ads not currently displayed)

### P3 - Backlog
- Order tracking page improvements
- Sales analytics dashboard
- Trustpilot / Take.app integrations
- Public referral program
- Clean up unused Google OAuth code (AuthCallback.jsx and backend endpoint)
