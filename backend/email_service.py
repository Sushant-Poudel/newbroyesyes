"""
Email Service Module
Handles all email notifications for the platform
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

# Email configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "noreply@gameshopnepal.com")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "GameShop Nepal")
SITE_URL = os.environ.get("SITE_URL", "https://gameshopnepal.com")

def send_email(to_email: str, subject: str, html_body: str, text_body: Optional[str] = None):
    """Send email via SMTP"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email not sent.")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        
        # Add text and HTML versions
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def get_base_email_template(content: str, preview_text: str = "") -> str:
    """Base email template with modern design"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title>GameShop Nepal</title>
        <!--[if !mso]><!-->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <!--<![endif]-->
        <style>
            body {{ margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .email-container {{ max-width: 600px; margin: 0 auto; }}
            @media screen and (max-width: 600px) {{
                .email-container {{ width: 100% !important; }}
                .stack-column {{ display: block !important; width: 100% !important; }}
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #0a0a0a; -webkit-font-smoothing: antialiased;">
        <!-- Preview text -->
        <div style="display: none; max-height: 0; overflow: hidden;">{preview_text}</div>
        
        <!-- Email Container -->
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #0a0a0a;">
            <tr>
                <td align="center" style="padding: 20px 10px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" class="email-container" style="background-color: #111111; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
                        
                        <!-- Header -->
                        <tr>
                            <td style="padding: 30px 40px; background: linear-gradient(135deg, #1a1a1a 0%, #111111 100%); border-bottom: 1px solid rgba(245, 166, 35, 0.2);">
                                <table role="presentation" width="100%">
                                    <tr>
                                        <td>
                                            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #F5A623; letter-spacing: -0.5px;">GSN</h1>
                                            <p style="margin: 5px 0 0; font-size: 12px; color: #666; letter-spacing: 1px; text-transform: uppercase;">GameShop Nepal</p>
                                        </td>
                                        <td align="right">
                                            <a href="{SITE_URL}" style="display: inline-block; padding: 10px 20px; background-color: rgba(245, 166, 35, 0.1); color: #F5A623; text-decoration: none; border-radius: 8px; font-size: 13px; font-weight: 500; border: 1px solid rgba(245, 166, 35, 0.2);">Visit Store</a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        {content}
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px; background-color: #0d0d0d; border-top: 1px solid #222;">
                                <table role="presentation" width="100%">
                                    <tr>
                                        <td align="center" style="padding-bottom: 20px;">
                                            <p style="margin: 0 0 10px; font-size: 14px; color: #888;">Need help? We're here for you!</p>
                                            <a href="https://wa.me/9779743488871" style="display: inline-block; padding: 12px 24px; background-color: #25D366; color: #fff; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600;">
                                                💬 Chat on WhatsApp
                                            </a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">
                                            <p style="margin: 0; font-size: 12px; color: #555;">
                                                © 2024 GameShop Nepal. All rights reserved.
                                            </p>
                                            <p style="margin: 10px 0 0; font-size: 11px; color: #444;">
                                                <a href="{SITE_URL}" style="color: #666; text-decoration: none;">Website</a> &nbsp;•&nbsp;
                                                <a href="{SITE_URL}/faq" style="color: #666; text-decoration: none;">FAQs</a> &nbsp;•&nbsp;
                                                <a href="{SITE_URL}/about" style="color: #666; text-decoration: none;">About Us</a>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def get_order_confirmation_email(order_data: dict) -> tuple:
    """Generate beautiful order confirmation email"""
    order_number = order_data.get('takeapp_order_number', order_data['id'][:8].upper())
    subject = f"🎉 Order Confirmed - #{order_number}"
    
    items_html = ""
    for item in order_data.get("items", []):
        item_name = item.get('name', 'Product')
        item_variation = item.get('variation', item.get('variation_name', ''))
        variation_text = f" • {item_variation}" if item_variation else ""
        items_html += f"""
        <tr>
            <td style="padding: 16px 0; border-bottom: 1px solid #222;">
                <table role="presentation" width="100%">
                    <tr>
                        <td style="width: 50px; vertical-align: top;">
                            <div style="width: 44px; height: 44px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 20px;">📦</span>
                            </div>
                        </td>
                        <td style="padding-left: 12px; vertical-align: top;">
                            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #fff;">{item_name}</p>
                            <p style="margin: 4px 0 0; font-size: 13px; color: #888;">{variation_text} × {item.get('quantity', 1)}</p>
                        </td>
                        <td align="right" style="vertical-align: top;">
                            <p style="margin: 0; font-size: 15px; font-weight: 600; color: #F5A623;">Rs {item.get('price', 0):,.0f}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    content = f"""
        <!-- Hero Section -->
        <tr>
            <td style="padding: 50px 40px; text-align: center; background: linear-gradient(180deg, rgba(245, 166, 35, 0.08) 0%, transparent 100%);">
                <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 30px rgba(245, 166, 35, 0.3);">
                    <span style="font-size: 40px;">✓</span>
                </div>
                <h2 style="margin: 0 0 10px; font-size: 28px; font-weight: 700; color: #fff;">Order Confirmed!</h2>
                <p style="margin: 0; font-size: 16px; color: #888;">Thank you for shopping with us, {order_data.get('customer_name', 'Customer')}!</p>
            </td>
        </tr>
        
        <!-- Order Info Card -->
        <tr>
            <td style="padding: 0 40px;">
                <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; overflow: hidden; border: 1px solid #2a2a2a;">
                    <tr>
                        <td style="padding: 20px;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td style="width: 50%;">
                                        <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Order Number</p>
                                        <p style="margin: 5px 0 0; font-size: 18px; font-weight: 700; color: #F5A623;">#{order_number}</p>
                                    </td>
                                    <td style="width: 50%;" align="right">
                                        <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Date</p>
                                        <p style="margin: 5px 0 0; font-size: 16px; font-weight: 500; color: #fff;">{order_data.get('created_at', '')[:10]}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- Items Section -->
        <tr>
            <td style="padding: 30px 40px 20px;">
                <h3 style="margin: 0 0 20px; font-size: 16px; font-weight: 600; color: #fff; text-transform: uppercase; letter-spacing: 0.5px;">Order Items</h3>
                <table role="presentation" width="100%">
                    {items_html}
                </table>
            </td>
        </tr>
        
        <!-- Total Section -->
        <tr>
            <td style="padding: 0 40px 30px;">
                <table role="presentation" width="100%" style="background: linear-gradient(135deg, #1a1a1a 0%, #151515 100%); border-radius: 12px; border: 1px solid #2a2a2a;">
                    <tr>
                        <td style="padding: 20px;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td><p style="margin: 0; font-size: 14px; color: #888;">Subtotal</p></td>
                                    <td align="right"><p style="margin: 0; font-size: 14px; color: #fff;">Rs {order_data.get('subtotal', order_data.get('total_amount', 0)):,.0f}</p></td>
                                </tr>
                                {f'''<tr>
                                    <td><p style="margin: 8px 0 0; font-size: 14px; color: #888;">Discount</p></td>
                                    <td align="right"><p style="margin: 8px 0 0; font-size: 14px; color: #22c55e;">-Rs {order_data.get('discount', 0):,.0f}</p></td>
                                </tr>''' if order_data.get('discount') else ''}
                                <tr>
                                    <td colspan="2" style="padding-top: 15px; border-top: 1px solid #2a2a2a; margin-top: 15px;">
                                        <table role="presentation" width="100%">
                                            <tr>
                                                <td><p style="margin: 0; font-size: 18px; font-weight: 700; color: #fff;">Total</p></td>
                                                <td align="right"><p style="margin: 0; font-size: 24px; font-weight: 700; color: #F5A623;">Rs {order_data.get('total_amount', 0):,.0f}</p></td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- What's Next Section -->
        <tr>
            <td style="padding: 0 40px 40px;">
                <table role="presentation" width="100%" style="background-color: rgba(245, 166, 35, 0.05); border-radius: 12px; border: 1px solid rgba(245, 166, 35, 0.15);">
                    <tr>
                        <td style="padding: 25px;">
                            <h4 style="margin: 0 0 15px; font-size: 14px; font-weight: 600; color: #F5A623; text-transform: uppercase; letter-spacing: 0.5px;">⚡ What happens next?</h4>
                            <table role="presentation" width="100%">
                                <tr>
                                    <td style="width: 30px; vertical-align: top;"><span style="font-size: 16px;">1️⃣</span></td>
                                    <td style="padding-bottom: 10px;"><p style="margin: 0; font-size: 14px; color: #ccc;">We'll verify your payment</p></td>
                                </tr>
                                <tr>
                                    <td style="width: 30px; vertical-align: top;"><span style="font-size: 16px;">2️⃣</span></td>
                                    <td style="padding-bottom: 10px;"><p style="margin: 0; font-size: 14px; color: #ccc;">Your digital product will be delivered instantly</p></td>
                                </tr>
                                <tr>
                                    <td style="width: 30px; vertical-align: top;"><span style="font-size: 16px;">3️⃣</span></td>
                                    <td><p style="margin: 0; font-size: 14px; color: #ccc;">Check your email for product details</p></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    """
    
    html = get_base_email_template(content, f"Your order #{order_number} has been confirmed!")
    
    text = f"""
ORDER CONFIRMED! 🎉

Thank you for your order at GameShop Nepal!

Order Number: #{order_number}
Date: {order_data.get('created_at', '')[:10]}
Customer: {order_data.get('customer_name')}

Total: Rs {order_data.get('total_amount'):,.0f}

What's next?
1. We'll verify your payment
2. Your digital product will be delivered instantly
3. Check your email for product details

Need help? WhatsApp us: +977 9743488871

GameShop Nepal
{SITE_URL}
    """
    
    return subject, html, text


def get_order_status_update_email(order_data: dict, new_status: str) -> tuple:
    """Generate order status update email"""
    order_number = order_data.get('takeapp_order_number', order_data['id'][:8].upper())
    
    status_config = {
        "pending": {"emoji": "⏳", "color": "#eab308", "message": "Your order is waiting for payment confirmation"},
        "confirmed": {"emoji": "✅", "color": "#3b82f6", "message": "Payment received! We're preparing your order"},
        "processing": {"emoji": "⚙️", "color": "#8b5cf6", "message": "Your order is being processed"},
        "completed": {"emoji": "🎉", "color": "#22c55e", "message": "Your order is complete! Check your email for details"},
        "delivered": {"emoji": "📦", "color": "#22c55e", "message": "Your digital product has been delivered!"},
        "cancelled": {"emoji": "❌", "color": "#ef4444", "message": "Your order has been cancelled"}
    }
    
    config = status_config.get(new_status.lower(), status_config["pending"])
    subject = f"{config['emoji']} Order #{order_number} - {new_status.title()}"
    
    content = f"""
        <!-- Status Update -->
        <tr>
            <td style="padding: 50px 40px; text-align: center;">
                <div style="width: 80px; height: 80px; margin: 0 auto 20px; background-color: {config['color']}20; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid {config['color']};">
                    <span style="font-size: 40px;">{config['emoji']}</span>
                </div>
                <h2 style="margin: 0 0 10px; font-size: 24px; font-weight: 700; color: #fff;">Order Status Updated</h2>
                <p style="margin: 0; font-size: 16px; color: #888;">{config['message']}</p>
            </td>
        </tr>
        
        <!-- Order Details Card -->
        <tr>
            <td style="padding: 0 40px 40px;">
                <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a;">
                    <tr>
                        <td style="padding: 25px;">
                            <table role="presentation" width="100%">
                                <tr>
                                    <td>
                                        <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Order Number</p>
                                        <p style="margin: 5px 0 0; font-size: 18px; font-weight: 700; color: #F5A623;">#{order_number}</p>
                                    </td>
                                    <td align="right">
                                        <p style="margin: 0; font-size: 12px; color: #666; text-transform: uppercase;">Status</p>
                                        <p style="margin: 5px 0 0; font-size: 16px; font-weight: 600; color: {config['color']};">{new_status.upper()}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- CTA Button -->
        <tr>
            <td style="padding: 0 40px 40px; text-align: center;">
                <a href="{SITE_URL}/account" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); color: #000; text-decoration: none; border-radius: 10px; font-size: 15px; font-weight: 600; box-shadow: 0 4px 15px rgba(245, 166, 35, 0.3);">
                    View Order Details
                </a>
            </td>
        </tr>
    """
    
    html = get_base_email_template(content, f"Order #{order_number} is now {new_status}")
    
    text = f"""
ORDER STATUS UPDATE

{config['emoji']} {config['message']}

Order Number: #{order_number}
Status: {new_status.upper()}

View your order: {SITE_URL}/account

Need help? WhatsApp us: +977 9743488871

GameShop Nepal
    """
    
    return subject, html, text


def get_welcome_email(customer_name: str) -> tuple:
    """Generate beautiful welcome email for new customers"""
    subject = "🎉 Welcome to GameShop Nepal!"
    
    content = f"""
        <!-- Welcome Hero -->
        <tr>
            <td style="padding: 50px 40px; text-align: center; background: linear-gradient(180deg, rgba(245, 166, 35, 0.1) 0%, transparent 100%);">
                <div style="width: 90px; height: 90px; margin: 0 auto 25px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 10px 40px rgba(245, 166, 35, 0.4);">
                    <span style="font-size: 45px;">👋</span>
                </div>
                <h2 style="margin: 0 0 10px; font-size: 32px; font-weight: 700; color: #fff;">Welcome, {customer_name}!</h2>
                <p style="margin: 0; font-size: 16px; color: #888; max-width: 400px; margin: 0 auto;">You've joined Nepal's most trusted destination for digital products</p>
            </td>
        </tr>
        
        <!-- Features Grid -->
        <tr>
            <td style="padding: 0 40px 30px;">
                <table role="presentation" width="100%">
                    <tr>
                        <td style="width: 50%; padding-right: 10px; vertical-align: top;">
                            <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a;">
                                <tr>
                                    <td style="padding: 20px; text-align: center;">
                                        <span style="font-size: 30px;">⚡</span>
                                        <p style="margin: 10px 0 5px; font-size: 14px; font-weight: 600; color: #fff;">Instant Delivery</p>
                                        <p style="margin: 0; font-size: 12px; color: #666;">Get your products in minutes</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                        <td style="width: 50%; padding-left: 10px; vertical-align: top;">
                            <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a;">
                                <tr>
                                    <td style="padding: 20px; text-align: center;">
                                        <span style="font-size: 30px;">💯</span>
                                        <p style="margin: 10px 0 5px; font-size: 14px; font-weight: 600; color: #fff;">100% Genuine</p>
                                        <p style="margin: 0; font-size: 12px; color: #666;">Authentic products only</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="height: 15px;"></td>
                    </tr>
                    <tr>
                        <td style="width: 50%; padding-right: 10px; vertical-align: top;">
                            <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a;">
                                <tr>
                                    <td style="padding: 20px; text-align: center;">
                                        <span style="font-size: 30px;">💰</span>
                                        <p style="margin: 10px 0 5px; font-size: 14px; font-weight: 600; color: #fff;">Best Prices</p>
                                        <p style="margin: 0; font-size: 12px; color: #666;">Lowest prices in Nepal</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                        <td style="width: 50%; padding-left: 10px; vertical-align: top;">
                            <table role="presentation" width="100%" style="background-color: #1a1a1a; border-radius: 12px; border: 1px solid #2a2a2a;">
                                <tr>
                                    <td style="padding: 20px; text-align: center;">
                                        <span style="font-size: 30px;">🎁</span>
                                        <p style="margin: 10px 0 5px; font-size: 14px; font-weight: 600; color: #fff;">Earn Rewards</p>
                                        <p style="margin: 0; font-size: 12px; color: #666;">Get cashback on orders</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- Popular Products -->
        <tr>
            <td style="padding: 0 40px 30px;">
                <table role="presentation" width="100%" style="background: linear-gradient(135deg, rgba(245, 166, 35, 0.1) 0%, rgba(245, 166, 35, 0.05) 100%); border-radius: 12px; border: 1px solid rgba(245, 166, 35, 0.2);">
                    <tr>
                        <td style="padding: 25px;">
                            <h4 style="margin: 0 0 15px; font-size: 14px; font-weight: 600; color: #F5A623; text-transform: uppercase; letter-spacing: 0.5px;">🔥 Popular Products</h4>
                            <p style="margin: 0 0 5px; font-size: 14px; color: #ccc;">• Netflix Premium - Starting Rs 299</p>
                            <p style="margin: 0 0 5px; font-size: 14px; color: #ccc;">• Spotify Premium - Starting Rs 149</p>
                            <p style="margin: 0 0 5px; font-size: 14px; color: #ccc;">• YouTube Premium - Starting Rs 149</p>
                            <p style="margin: 0; font-size: 14px; color: #ccc;">• And many more!</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        
        <!-- CTA Button -->
        <tr>
            <td style="padding: 0 40px 40px; text-align: center;">
                <a href="{SITE_URL}" style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); color: #000; text-decoration: none; border-radius: 12px; font-size: 16px; font-weight: 700; box-shadow: 0 4px 20px rgba(245, 166, 35, 0.4);">
                    Start Shopping Now
                </a>
            </td>
        </tr>
    """
    
    html = get_base_email_template(content, f"Welcome to GameShop Nepal, {customer_name}!")
    
    text = f"""
WELCOME TO GAMESHOP NEPAL! 🎉

Hi {customer_name},

Thank you for joining GameShop Nepal - Nepal's most trusted destination for digital products!

WHY CHOOSE US:
✓ Instant Digital Delivery
✓ 100% Genuine Products
✓ Best Prices in Nepal
✓ Earn Cashback Rewards

POPULAR PRODUCTS:
• Netflix Premium - Starting Rs 299
• Spotify Premium - Starting Rs 149
• YouTube Premium - Starting Rs 149
• And many more!

Start shopping: {SITE_URL}

Need help? WhatsApp us: +977 9743488871

GameShop Nepal
    """
    
    return subject, html, text


def get_otp_email(email: str, otp: str) -> tuple:
    """Generate OTP verification email"""
    subject = "🔐 Your Login Code - GameShop Nepal"
    
    content = f"""
        <!-- OTP Section -->
        <tr>
            <td style="padding: 50px 40px; text-align: center;">
                <div style="width: 70px; height: 70px; margin: 0 auto 20px; background: linear-gradient(135deg, #F5A623 0%, #f59e0b 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 35px;">🔐</span>
                </div>
                <h2 style="margin: 0 0 10px; font-size: 24px; font-weight: 700; color: #fff;">Verification Code</h2>
                <p style="margin: 0 0 30px; font-size: 15px; color: #888;">Enter this code to login to your account</p>
                
                <!-- OTP Display -->
                <div style="background-color: #1a1a1a; border-radius: 16px; padding: 25px 40px; display: inline-block; border: 2px solid #F5A623;">
                    <p style="margin: 0; font-size: 42px; font-weight: 700; color: #F5A623; letter-spacing: 12px; font-family: 'Courier New', monospace;">{otp}</p>
                </div>
                
                <p style="margin: 25px 0 0; font-size: 13px; color: #666;">This code expires in 10 minutes</p>
            </td>
        </tr>
        
        <!-- Security Notice -->
        <tr>
            <td style="padding: 0 40px 40px;">
                <table role="presentation" width="100%" style="background-color: rgba(239, 68, 68, 0.1); border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.2);">
                    <tr>
                        <td style="padding: 20px;">
                            <p style="margin: 0; font-size: 13px; color: #f87171;">
                                ⚠️ <strong>Security Notice:</strong> Never share this code with anyone. GameShop Nepal staff will never ask for your OTP.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    """
    
    html = get_base_email_template(content, f"Your login code is {otp}")
    
    text = f"""
VERIFICATION CODE

Your login code for GameShop Nepal is:

{otp}

This code expires in 10 minutes.

⚠️ Security Notice: Never share this code with anyone.

GameShop Nepal
{SITE_URL}
    """
    
    return subject, html, text
