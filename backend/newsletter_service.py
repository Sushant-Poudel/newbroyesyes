"""
Newsletter Service Module
Handles bulk newsletter sending with preset templates
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict
import logging
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)

# Newsletter SMTP configuration (using same as main SMTP)
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "gameshopnepal.buy@gmail.com")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "GameShop Nepal")

# Preset Newsletter Templates
NEWSLETTER_TEMPLATES = {
    "new_product": {
        "name": "New Product Launch",
        "subject": "🚀 New Product Alert: {product_name} is Here!",
        "description": "Announce a new product to your customers",
        "variables": ["product_name", "product_description", "product_price", "product_image", "product_link"],
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #000000; color: #ffffff;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
            <h1 style="margin: 0; color: #F5A623; font-size: 28px; font-weight: bold;">GSN</h1>
            <p style="margin: 10px 0 0; color: #888;">GameShop Nepal</p>
        </div>
        
        <!-- New Product Banner -->
        <div style="text-align: center; padding: 40px 20px; background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%); margin: 20px 0; border-radius: 12px; border: 1px solid #F5A623;">
            <span style="background: #F5A623; color: #000; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold;">NEW ARRIVAL</span>
            <h2 style="color: #ffffff; font-size: 32px; margin: 20px 0 10px;">{product_name}</h2>
            <p style="color: #888; font-size: 16px; margin: 0;">{product_description}</p>
        </div>
        
        <!-- Product Image -->
        {product_image_section}
        
        <!-- Price & CTA -->
        <div style="text-align: center; padding: 30px 0;">
            <p style="color: #F5A623; font-size: 36px; font-weight: bold; margin: 0 0 20px;">Rs {product_price}</p>
            <a href="{product_link}" style="display: inline-block; background: #F5A623; color: #000; padding: 15px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                Shop Now →
            </a>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a; margin-top: 20px;">
            <p style="color: #666; margin: 5px 0; font-size: 12px;">GameShop Nepal - Your Trusted Digital Store</p>
            <p style="color: #666; margin: 5px 0; font-size: 11px;">
                <a href="{unsubscribe_link}" style="color: #666;">Unsubscribe</a> | <a href="{website_link}" style="color: #666;">Visit Website</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "sale_announcement": {
        "name": "Sale Announcement",
        "subject": "🔥 {sale_name} - Up to {discount_percent}% OFF!",
        "description": "Announce a sale or special discount",
        "variables": ["sale_name", "discount_percent", "sale_description", "end_date", "shop_link"],
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #000000; color: #ffffff;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
            <h1 style="margin: 0; color: #F5A623; font-size: 28px; font-weight: bold;">GSN</h1>
        </div>
        
        <!-- Sale Banner -->
        <div style="text-align: center; padding: 50px 20px; background: linear-gradient(135deg, #F5A623 0%, #FF6B35 100%); margin: 20px 0; border-radius: 12px;">
            <h2 style="color: #000; font-size: 42px; margin: 0; font-weight: 900;">{sale_name}</h2>
            <p style="color: #000; font-size: 72px; font-weight: 900; margin: 10px 0;">{discount_percent}% OFF</p>
            <p style="color: #000; font-size: 16px; margin: 0;">{sale_description}</p>
        </div>
        
        <!-- Countdown -->
        <div style="text-align: center; padding: 20px; background: #1a1a1a; border-radius: 8px; margin: 20px 0;">
            <p style="color: #F5A623; margin: 0; font-size: 14px;">⏰ Sale ends: <strong>{end_date}</strong></p>
        </div>
        
        <!-- CTA -->
        <div style="text-align: center; padding: 30px 0;">
            <a href="{shop_link}" style="display: inline-block; background: #F5A623; color: #000; padding: 18px 60px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 18px;">
                SHOP THE SALE →
            </a>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a; margin-top: 20px;">
            <p style="color: #666; margin: 5px 0; font-size: 12px;">GameShop Nepal</p>
            <p style="color: #666; margin: 5px 0; font-size: 11px;">
                <a href="{unsubscribe_link}" style="color: #666;">Unsubscribe</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "weekly_update": {
        "name": "Weekly Update",
        "subject": "📬 This Week at GameShop Nepal",
        "description": "Weekly newsletter with updates and highlights",
        "variables": ["greeting_text", "highlight_1", "highlight_2", "highlight_3", "featured_product", "featured_price", "shop_link"],
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #000000; color: #ffffff;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
            <h1 style="margin: 0; color: #F5A623; font-size: 28px; font-weight: bold;">GSN Weekly</h1>
            <p style="margin: 10px 0 0; color: #888;">Your Digital Products Update</p>
        </div>
        
        <!-- Greeting -->
        <div style="padding: 30px 0;">
            <p style="color: #cccccc; font-size: 16px; line-height: 1.8;">{greeting_text}</p>
        </div>
        
        <!-- Highlights -->
        <div style="background: #0A0A0A; border: 1px solid #2a2a2a; border-radius: 12px; padding: 25px; margin: 20px 0;">
            <h3 style="color: #F5A623; margin: 0 0 20px; font-size: 18px;">📌 This Week's Highlights</h3>
            <ul style="color: #cccccc; line-height: 2.2; padding-left: 20px; margin: 0;">
                <li>{highlight_1}</li>
                <li>{highlight_2}</li>
                <li>{highlight_3}</li>
            </ul>
        </div>
        
        <!-- Featured Product -->
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%); border-radius: 12px; border: 1px solid #F5A623; margin: 20px 0;">
            <span style="color: #F5A623; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Featured This Week</span>
            <h3 style="color: #fff; font-size: 24px; margin: 15px 0;">{featured_product}</h3>
            <p style="color: #F5A623; font-size: 28px; font-weight: bold; margin: 10px 0;">Rs {featured_price}</p>
            <a href="{shop_link}" style="display: inline-block; background: #F5A623; color: #000; padding: 12px 35px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 15px;">
                View Product
            </a>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a; margin-top: 20px;">
            <p style="color: #888; margin: 5px 0;">See you next week! 👋</p>
            <p style="color: #666; margin: 15px 0 5px; font-size: 11px;">
                <a href="{unsubscribe_link}" style="color: #666;">Unsubscribe</a> | <a href="{website_link}" style="color: #666;">Visit Store</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "restock_alert": {
        "name": "Restock Alert",
        "subject": "🔔 {product_name} is Back in Stock!",
        "description": "Notify customers about restocked products",
        "variables": ["product_name", "product_description", "product_price", "shop_link"],
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #000000; color: #ffffff;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
            <h1 style="margin: 0; color: #F5A623; font-size: 28px; font-weight: bold;">GSN</h1>
        </div>
        
        <!-- Alert Banner -->
        <div style="text-align: center; padding: 40px 20px; background: #0A0A0A; border: 2px solid #10B981; margin: 20px 0; border-radius: 12px;">
            <span style="background: #10B981; color: #fff; padding: 8px 20px; border-radius: 20px; font-size: 14px; font-weight: bold;">✓ BACK IN STOCK</span>
            <h2 style="color: #ffffff; font-size: 28px; margin: 25px 0 10px;">{product_name}</h2>
            <p style="color: #888; font-size: 14px; margin: 0;">{product_description}</p>
            <p style="color: #F5A623; font-size: 32px; font-weight: bold; margin: 20px 0;">Rs {product_price}</p>
        </div>
        
        <!-- CTA -->
        <div style="text-align: center; padding: 20px 0;">
            <p style="color: #888; margin-bottom: 20px;">⚡ Limited stock available - Order now!</p>
            <a href="{shop_link}" style="display: inline-block; background: #10B981; color: #fff; padding: 15px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                Order Now →
            </a>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a; margin-top: 20px;">
            <p style="color: #666; margin: 5px 0; font-size: 12px;">GameShop Nepal</p>
            <p style="color: #666; margin: 5px 0; font-size: 11px;">
                <a href="{unsubscribe_link}" style="color: #666;">Unsubscribe</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    },
    
    "custom": {
        "name": "Custom Email",
        "subject": "{subject}",
        "description": "Create a custom newsletter from scratch",
        "variables": ["subject", "heading", "body_text", "button_text", "button_link"],
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #000000; color: #ffffff;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="text-align: center; padding: 30px 0; border-bottom: 2px solid #F5A623;">
            <h1 style="margin: 0; color: #F5A623; font-size: 28px; font-weight: bold;">GSN</h1>
            <p style="margin: 10px 0 0; color: #888;">GameShop Nepal</p>
        </div>
        
        <!-- Content -->
        <div style="padding: 40px 20px;">
            <h2 style="color: #F5A623; font-size: 28px; margin: 0 0 20px; text-align: center;">{heading}</h2>
            <div style="color: #cccccc; font-size: 16px; line-height: 1.8;">
                {body_text}
            </div>
        </div>
        
        <!-- CTA Button -->
        {button_section}
        
        <!-- Footer -->
        <div style="text-align: center; padding: 30px 0; border-top: 1px solid #2a2a2a; margin-top: 30px;">
            <p style="color: #666; margin: 5px 0; font-size: 12px;">GameShop Nepal - Your Trusted Digital Store</p>
            <p style="color: #666; margin: 5px 0; font-size: 11px;">
                <a href="{unsubscribe_link}" style="color: #666;">Unsubscribe</a> | <a href="{website_link}" style="color: #666;">Visit Website</a>
            </p>
        </div>
    </div>
</body>
</html>
"""
    }
}


def get_template_list() -> List[Dict]:
    """Get list of available templates"""
    return [
        {
            "id": key,
            "name": val["name"],
            "description": val["description"],
            "variables": val["variables"],
            "subject": val["subject"]
        }
        for key, val in NEWSLETTER_TEMPLATES.items()
    ]


def render_template(template_id: str, variables: Dict, website_url: str = "https://gameshopnepal.com") -> tuple:
    """Render a template with given variables"""
    if template_id not in NEWSLETTER_TEMPLATES:
        raise ValueError(f"Template '{template_id}' not found")
    
    template = NEWSLETTER_TEMPLATES[template_id]
    
    # Add default variables
    variables["unsubscribe_link"] = f"{website_url}/unsubscribe"
    variables["website_link"] = website_url
    
    # Handle product image section for new_product template
    if template_id == "new_product":
        if variables.get("product_image"):
            variables["product_image_section"] = f'''
            <div style="text-align: center; margin: 20px 0;">
                <img src="{variables['product_image']}" alt="{variables.get('product_name', 'Product')}" 
                     style="max-width: 100%; height: auto; border-radius: 12px; border: 1px solid #2a2a2a;">
            </div>
            '''
        else:
            variables["product_image_section"] = ""
    
    # Handle button section for custom template
    if template_id == "custom":
        if variables.get("button_text") and variables.get("button_link"):
            variables["button_section"] = f'''
            <div style="text-align: center; padding: 20px 0;">
                <a href="{variables['button_link']}" style="display: inline-block; background: #F5A623; color: #000; padding: 15px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                    {variables['button_text']}
                </a>
            </div>
            '''
        else:
            variables["button_section"] = ""
    
    # Render subject
    subject = template["subject"]
    for key, value in variables.items():
        subject = subject.replace("{" + key + "}", str(value))
    
    # Render HTML
    html = template["html"]
    for key, value in variables.items():
        html = html.replace("{" + key + "}", str(value))
    
    return subject, html


def send_newsletter(to_emails: List[str], subject: str, html_body: str) -> Dict:
    """Send newsletter to multiple recipients"""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured")
        return {"success": False, "error": "SMTP not configured", "sent": 0, "failed": 0}
    
    sent_count = 0
    failed_count = 0
    failed_emails = []
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            
            for email in to_emails:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = subject
                    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
                    msg["To"] = email
                    msg.attach(MIMEText(html_body, "html"))
                    
                    server.send_message(msg)
                    sent_count += 1
                    logger.info(f"Newsletter sent to {email}")
                except Exception as e:
                    failed_count += 1
                    failed_emails.append(email)
                    logger.error(f"Failed to send newsletter to {email}: {e}")
    except Exception as e:
        logger.error(f"SMTP connection error: {e}")
        return {"success": False, "error": str(e), "sent": sent_count, "failed": failed_count}
    
    return {
        "success": True,
        "sent": sent_count,
        "failed": failed_count,
        "failed_emails": failed_emails
    }
