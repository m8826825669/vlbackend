from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _site():
    return getattr(settings, 'SITE_NAME', 'Vexen Labs')


def _support():
    return getattr(settings, 'SUPPORT_EMAIL', 'support@vexenlabs.com')


def _phone():
    return getattr(settings, 'CONTACT_PHONE', '+91 91295 82882')


def send_purchase_confirmation(order, license_key: str):
    """Send purchase confirmation email with license key to the buyer."""
    product_name = order.plan.product.name
    plan_name    = order.plan.name

    if order.plan.billing_cycle == 'one_time':
        expires_info = 'Lifetime (no expiry)'
    elif order.plan.billing_cycle == 'annual':
        expires_info = '1 year from purchase date'
    else:
        expires_info = '1 month from purchase date'

    subject = f"🎉 Your {product_name} License Key — Order #{order.order_number}"

    message = f"""
Hi {order.billing_name},

Thank you for your purchase! Your license is ready.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ORDER DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Product     : {product_name}
Plan        : {plan_name}
Order No    : {order.order_number}
Amount Paid : ₹{order.total_amount:,.0f} (incl. 18% GST)
Date        : {order.completed_at.strftime('%d %b %Y, %I:%M %p IST') if order.completed_at else '—'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  YOUR LICENSE KEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  {license_key}

  ↳ Keep this key safe — it's tied to your account.
  ↳ Validity: {expires_info}
  ↳ Activations: {order.plan.max_devices} device(s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NEXT STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Log in to your dashboard: {settings.SITE_URL}/dashboard
2. Go to "My Licenses" tab
3. Click "Download Installer" to get the file
4. Install and enter your license key when prompted

Need help? Reply to this email or WhatsApp us at {_phone()}.
We respond within 4 hours on business days (9 AM – 6 PM IST).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_site()}
{settings.SITE_URL}
{_support()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a transactional email. You received this because you made a purchase on {_site()}.
"""

    try:
        send_mail(
            subject=subject,
            message=message.strip(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.billing_email],
            fail_silently=False,
        )
        logger.info(f"Purchase confirmation sent to {order.billing_email} for order {order.order_number}")
    except Exception as e:
        logger.error(f"Failed to send purchase confirmation to {order.billing_email}: {e}")


def send_password_reset_email(user, reset_url: str):
    """Send password reset email."""
    subject = f"Reset your {_site()} password"
    message = f"""
Hi {user.first_name or user.email},

You requested a password reset for your {_site()} account.

Click the link below to reset your password (valid for 1 hour):
{reset_url}

If you didn't request this, you can safely ignore this email.
Your password won't change until you click the link above.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{_site()}
{_support()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    try:
        send_mail(subject, message.strip(), settings.DEFAULT_FROM_EMAIL,
                  [user.email], fail_silently=True)
    except Exception as e:
        logger.error(f"Failed to send password reset to {user.email}: {e}")
