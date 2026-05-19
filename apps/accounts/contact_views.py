from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.mail import EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def contact_form(request):
    """Receive contact form and email support team + auto-reply to sender."""
    name     = request.data.get('name', '').strip()
    email    = request.data.get('email', '').strip()
    subject  = request.data.get('subject', '').strip()
    category = request.data.get('category', 'other').strip()
    message  = request.data.get('message', '').strip()

    if not all([name, email, subject, message]):
        return Response({'detail': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(message) < 20:
        return Response({'detail': 'Message must be at least 20 characters.'}, status=status.HTTP_400_BAD_REQUEST)

    site_name = getattr(settings, 'SITE_NAME', 'Vexen Labs')
    support_email = getattr(settings, 'SUPPORT_EMAIL', 'support@vexenlabs.com')
    contact_phone = getattr(settings, 'CONTACT_PHONE', '+91 91295 82882')

    body = f"""New contact form submission from {site_name}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CONTACT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name     : {name}
Email    : {email}
Category : {category}
Subject  : {subject}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MESSAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply directly to this email to respond to the customer.
"""
    try:
        # Email to support team with reply-to set to customer
        EmailMessage(
            subject=f"[Contact — {category.upper()}] {subject}",
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[support_email],
            reply_to=[f"{name} <{email}>"],
        ).send()

        # Auto-reply to the customer
        EmailMessage(
            subject=f"We received your message — {site_name}",
            body=f"""Hi {name},

Thank you for contacting {site_name}!

We've received your message about "{subject}" and will get back to you within 24 hours on business days (9 AM – 6 PM IST, Mon–Sat).

If your query is urgent, WhatsApp us at {contact_phone}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{site_name}
{settings.SITE_URL}
{support_email}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        ).send()

        logger.info(f"Contact form from {email}: {subject}")
        return Response({'detail': "Your message has been sent. We'll reply within 24 hours."})
    except Exception as e:
        logger.error(f"Contact form email failed: {e}")
        return Response(
            {'detail': f'Failed to send. Please email {support_email} directly.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
