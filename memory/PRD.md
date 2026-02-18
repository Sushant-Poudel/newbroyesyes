# GameShop Nepal - Product Requirements Document

## Original Problem Statement
Clone and set up the GameShop Nepal e-commerce application from GitHub repository (https://github.com/Sushant-Poudel/GANGULI-Wata). Configure SMTP and ImgBB credentials.

## Architecture
- **Frontend**: React 19 with React Router, Tailwind CSS, shadcn/ui components
- **Backend**: FastAPI (Python) with Motor async MongoDB driver
- **Database**: MongoDB
- **Hosting**: Kubernetes container with nginx proxy

## User Personas
1. **Customers**: Browse products, purchase digital items, earn daily rewards & referral credits
2. **Admins**: Manage products, orders, customers, promotions, and staff

## Core Features (Implemented)

### Customer Features
- OTP-based email authentication
- Product browsing with categories
- Shopping cart & checkout
- Order tracking
- Daily login rewards
- Referral program
- Store credits system

### Admin Features
- Dashboard with analytics
- Product & category management
- Order management
- Customer management
- Staff management with permissions
- Promo codes & pricing settings
- Blog management
- FAQ & page content management
- Email notifications (SMTP configured)
- ImgBB image uploads configured

## Configuration (Completed: Feb 18, 2026)
- ✅ SMTP: gameshopnepal.buy@gmail.com
- ✅ ImgBB API Key: Configured
- ✅ MongoDB: Local instance
- ✅ All services running

## Admin Credentials
- Username: `gsnadmin`
- Password: `gsnadmin`

## URLs
- Frontend: https://git-sync-13.preview.emergentagent.com
- Admin: https://git-sync-13.preview.emergentagent.com/panelgsnadminbackend/login

## Testing Status
- Backend: 100% pass (18/18 tests)
- Frontend: 100% pass (all pages functional)

## Backlog / Future Features
- [ ] Seed sample products
- [ ] Spin the Wheel promotion
- [ ] Achievement badges
- [ ] Enhanced product filters
- [ ] Customer analytics dashboard

## Update Log

### Feb 18, 2026 - Required Fields Update
- Made **phone number** and **email** compulsory for:
  - Customer login (OTP authentication)
  - Order creation (checkout & product page)
- Backend validation added in Pydantic models
- Frontend forms show asterisks (*) for required fields
- Both fields validated before form submission

### Feb 18, 2026 - Analytics Dashboard Redesign
- Redesigned analytics page with clean grid layout
- **4 KPI Cards**: Revenue, Orders, Profit, Visitors with color-coded gradients
- **Period Selector Tabs**: Today, Week, Month, All Time
- **Revenue Trend Chart**: Area chart with interactive period selector (7/30/90 days)
- **Order Status Chart**: Donut chart with color-coded legend
- **Top Products Table**: Clean table with ranking and revenue
- Fully responsive design (desktop, tablet, mobile)

### Feb 18, 2026 - Customer Account System Improvements
**Changes:**
- Removed wishlist system from account page
- Added "View Invoice" link to each order in order history
- Invoice page now displays payment screenshot if uploaded during checkout
- Added "Refresh" button to orders tab for retry on load failures
- Improved error handling to prevent "Failed to load data" errors
- Stats cards reduced to 4: Total Orders, Total Spent, Store Credits, Member Since

**Database:** Using MongoDB - good choice for e-commerce with flexible document structure

### Feb 18, 2026 - Newsletter System Added
**Features:**
- New admin section: Newsletter management at /admin/newsletter
- 5 preset email templates:
  1. **New Product Launch** - Announce new products with image, price, CTA
  2. **Sale Announcement** - Big sale banners with discount percentage
  3. **Weekly Update** - Weekly highlights and featured products
  4. **Restock Alert** - Notify customers when items are back
  5. **Custom Email** - Free-form custom newsletters
- Bulk send to: All contacts, Subscribed only, or Recent buyers (30 days)
- Send test email before bulk send
- Preview emails before sending
- Campaign history tracking

**SMTP:** Using `gameshopnepal.buy@gmail.com` (Gmail daily limit: 500 emails)

### Feb 18, 2026 - Admin Panel Sidebar Overhaul
**Problem:** 21 flat menu items - too cluttered and hard to navigate

**Solution:** Reorganized into 7 logical collapsible groups:
1. **Main** (always visible): Dashboard, Analytics, Orders
2. **Store**: Products, Categories, Reviews
3. **Customers**: All Customers, Staff Management
4. **Marketing**: Promo Codes, Newsletter, Notification Bar
5. **Rewards & Credits**: Store Credits, Daily Rewards, Referral Program, Multiplier Events
6. **Content**: Blog/Guides, Pages, FAQs
7. **Settings**: Pricing, Payment Methods, Social Links

**Features:**
- Collapsible groups with chevron icons
- Auto-expands group containing current page
- Permission-based visibility (staff see only allowed sections)
- Mobile responsive with slide-out menu
- Footer: View Store + Logout buttons

### Feb 18, 2026 - Review Carousel Fix
**Problem:** Review carousel moves too fast on mobile - users can't read reviews

**Solution:**
- Slowed down mobile animation from 80s to 120s (50% slower)
- Limited reviews to maximum 20 most recent (FIFO - new review pushes out oldest)
- Backend API now returns only 20 reviews sorted by date
- Frontend also enforces 20 limit as backup

### Feb 18, 2026 - WhatsApp Custom Fields
**Problem:** Custom form fields (like account email, game ID, etc.) not included in WhatsApp message

**Solution:**
- ProductPage now passes custom fields via URL params to PaymentPage
- Custom fields format in URL: `label:value||label:value`
- PaymentPage parses and includes in WhatsApp message
- Format in message: `*Field Label:* value`
- Also includes customer remarks/notes

**Affected Flows:**
- Single product order → WhatsApp
- Credits-paid order → WhatsApp
- Cart checkout (no custom fields, cart-based)
