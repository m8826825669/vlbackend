"""
Orders views — handles the full purchase lifecycle:
  1. create_order  → creates a DB order + Razorpay order, returns checkout payload
  2. verify_payment → verifies HMAC signature, marks order completed, generates license
  3. my_orders, order_detail, admin_orders → listing endpoints

Contract is aligned with the Next.js frontend (frontend/src/lib/api.ts).
"""
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import razorpay
import hmac
import hashlib
import logging

from .models import Order
from apps.products.models import Product, PricingPlan
from apps.licenses.models import License
from apps.licenses.utils import generate_license_key

logger = logging.getLogger(__name__)

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


# ─── Demo coupon table ──────────────────────────────────────────────────────
# In production, move this to a `Coupon` model. For now, this matches the
# coupons hardcoded on the frontend checkout page.
COUPONS = {
    'WELCOME10': Decimal('10'),
    'LAUNCH20':  Decimal('20'),
    'VEXEN5':    Decimal('5'),
}


def _order_to_dict(order):
    return {
        'id': str(order.id),
        'order_number': order.order_number,
        'status': order.status,
        'amount': float(order.amount),
        'tax_amount': float(order.tax_amount),
        'discount_amount': float(order.discount_amount),
        'total_amount': float(order.total_amount),
        'currency': order.currency,
        'razorpay_order_id': order.razorpay_order_id,
        'razorpay_payment_id': order.razorpay_payment_id,
        'plan_id': str(order.plan.id),
        'plan_name': order.plan.name,
        'product_name': order.plan.product.name,
        'product_slug': order.plan.product.slug,
        'product_emoji': order.plan.product.emoji,
        'billing_name': order.billing_name,
        'billing_email': order.billing_email,
        'billing_phone': order.billing_phone,
        'gst_number': order.gst_number,
        'invoice_number': order.invoice_number,
        'created_at': order.created_at.isoformat(),
        'completed_at': order.completed_at.isoformat() if order.completed_at else None,
    }


# ─── CREATE ORDER ───────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_order(request):
    """
    Frontend sends:
        {
            "product_slug": "school-erp",        # optional, for context
            "plan_id": "<uuid>",                  # required
            "amount": 11800,                      # optional, recomputed server-side
            "currency": "INR",
            "billing": {
                "name", "email", "phone", "company",
                "gstin", "address", "city", "state", "pincode"
            },
            "coupon_code": "WELCOME10"            # optional
        }
    Returns:
        {
            "id": "<order-uuid>",
            "order_number": "VL0000001234",
            "razorpay_order_id": "order_xxx",
            "razorpay_key": "rzp_xxx",
            "amount": <paise>,                    # for Razorpay checkout
            "currency": "INR",
            "name": "<product name>",
            "description": "<plan name> License",
            "prefill": { ... }
        }
    """
    plan_id = request.data.get('plan_id')
    if not plan_id:
        return Response({'detail': 'plan_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        plan = PricingPlan.objects.select_related('product').get(id=plan_id, is_active=True)
    except (PricingPlan.DoesNotExist, ValueError, Exception):
        return Response({'detail': 'Pricing plan not found.'}, status=status.HTTP_404_NOT_FOUND)

    # ─── Billing: accept either flat fields or a nested "billing" object ───
    billing = request.data.get('billing') or {}
    if not isinstance(billing, dict):
        billing = {}

    billing_name = (
        billing.get('name')
        or request.data.get('billing_name')
        or request.user.full_name
        or ''
    ).strip()
    billing_email = (
        billing.get('email')
        or request.data.get('billing_email')
        or request.user.email
        or ''
    ).strip()
    billing_phone = (
        billing.get('phone')
        or request.data.get('billing_phone')
        or request.user.phone
        or ''
    ).strip()
    billing_address_parts = [
        billing.get('address', ''),
        billing.get('city', ''),
        billing.get('state', ''),
        billing.get('pincode', ''),
    ]
    billing_address = ', '.join(p for p in billing_address_parts if p) \
        or request.data.get('billing_address', '')
    gst_number = (
        billing.get('gstin')
        or request.data.get('gstin')
        or request.data.get('gst_number', '')
    ).strip().upper()

    if not billing_name or not billing_email:
        return Response(
            {'detail': 'Billing name and email are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ─── Prevent duplicate purchase (active license already exists) ───
    existing = License.objects.filter(
        user=request.user, product=plan.product, is_active=True
    ).first()
    if existing:
        return Response(
            {'detail': f'You already own an active license for {plan.product.name}. Visit your dashboard.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ─── Pricing: ALWAYS recompute server-side. Never trust client amount. ───
    subtotal = Decimal(plan.price)
    discount = Decimal('0')
    coupon_code = (request.data.get('coupon_code') or '').strip().upper()
    if coupon_code:
        pct = COUPONS.get(coupon_code)
        if pct:
            discount = (subtotal * pct / Decimal('100')).quantize(Decimal('0.01'))
        else:
            return Response({'detail': 'Invalid coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

    taxable = subtotal - discount
    tax = (taxable * Decimal('0.18')).quantize(Decimal('0.01'))  # 18% GST
    total = (taxable + tax).quantize(Decimal('0.01'))

    # ─── Create the Razorpay order (amount in paise) ───
    try:
        razorpay_order = razorpay_client.order.create({
            'amount': int(total * 100),
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'user_id': str(request.user.id),
                'plan_id': str(plan.id),
                'coupon': coupon_code,
            },
        })
    except Exception as exc:
        logger.error(f'Razorpay order creation failed: {exc}')
        return Response(
            {'detail': 'Could not initialize payment gateway. Please try again.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # ─── Persist the DB order ───
    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            plan=plan,
            amount=subtotal,
            tax_amount=tax,
            discount_amount=discount,
            total_amount=total,
            currency='INR',
            razorpay_order_id=razorpay_order['id'],
            billing_name=billing_name,
            billing_email=billing_email,
            billing_phone=billing_phone,
            billing_address=billing_address,
            gst_number=gst_number,
            notes=f'coupon={coupon_code}' if coupon_code else '',
        )

    return Response({
        'id': str(order.id),
        'order_number': order.order_number,
        'razorpay_order_id': razorpay_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': int(total * 100),
        'currency': 'INR',
        'name': plan.product.name,
        'description': f'{plan.name} — {plan.product.name}',
        'prefill': {
            'name': billing_name,
            'email': billing_email,
            'contact': billing_phone,
        },
        'breakdown': {
            'subtotal': float(subtotal),
            'discount': float(discount),
            'tax': float(tax),
            'total': float(total),
        },
    }, status=status.HTTP_201_CREATED)


# ─── VERIFY PAYMENT ─────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_payment(request):
    """
    Frontend sends:
        {
            "razorpay_order_id":   "order_xxx",
            "razorpay_payment_id": "pay_xxx",
            "razorpay_signature":  "<hex>",
            "order_id":            "<our-order-uuid>"   # optional safety check
        }
    Returns:
        {
            "message": "...",
            "license_key": "XXXX-XXXX-XXXX-XXXX-XXXX",
            "order_number": "VL0000001234",
            "order_id": "<uuid>"
        }
    """
    razorpay_order_id   = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature  = request.data.get('razorpay_signature')
    our_order_id        = request.data.get('order_id')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return Response(
            {'detail': 'Missing payment confirmation fields.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        qs = Order.objects.filter(
            razorpay_order_id=razorpay_order_id, user=request.user
        )
        if our_order_id:
            qs = qs.filter(id=our_order_id)
        order = qs.select_related('plan__product').get()
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

    if order.status == 'completed':
        # Idempotent: already processed
        existing_license = License.objects.filter(order=order).first()
        return Response({
            'message': 'Order already processed.',
            'license_key': existing_license.license_key if existing_license else '',
            'order_number': order.order_number,
            'order_id': str(order.id),
        })

    # ─── Verify HMAC-SHA256 signature ───
    msg = f'{razorpay_order_id}|{razorpay_payment_id}'.encode()
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(), msg, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, razorpay_signature):
        order.status = 'failed'
        order.save(update_fields=['status', 'updated_at'])
        logger.warning(f'Signature mismatch for order {order.order_number}')
        return Response(
            {'detail': 'Payment signature verification failed.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ─── Mark completed + generate license atomically ───
    with transaction.atomic():
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = razorpay_signature
        order.status = 'completed'
        order.completed_at = timezone.now()
        if not order.invoice_number:
            order.invoice_number = f'INV-{order.order_number}'
        order.save()

        # Compute expiry from billing cycle
        expires_at = None
        if order.plan.billing_cycle == 'annual':
            expires_at = timezone.now() + timedelta(days=365)
        elif order.plan.billing_cycle == 'monthly':
            expires_at = timezone.now() + timedelta(days=30)

        # Generate license; loop in the (very unlikely) case of collision
        for _ in range(5):
            key = generate_license_key()
            if not License.objects.filter(license_key=key).exists():
                break

        license = License.objects.create(
            user=request.user,
            order=order,
            product=order.plan.product,
            plan=order.plan,
            license_key=key,
            max_activations=order.plan.max_devices,
            expires_at=expires_at,
        )

        # Update product purchase counter
        order.plan.product.total_purchases = order.plan.product.total_purchases + 1
        order.plan.product.save(update_fields=['total_purchases', 'updated_at'])

    # ─── Send confirmation email (best-effort) ───
    try:
        from .email_utils import send_purchase_confirmation
        send_purchase_confirmation(order, license.license_key)
    except Exception as exc:
        logger.error(f'Could not send purchase email: {exc}')

    return Response({
        'message': 'Payment verified successfully. License created.',
        'license_key': license.license_key,
        'license': {
            'id': str(license.id),
            'license_key': license.license_key,
        },
        'order_number': order.order_number,
        'order_id': str(order.id),
    })


# ─── LISTING ENDPOINTS ──────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_orders(request):
    orders = (
        Order.objects.filter(user=request.user)
        .select_related('plan__product')
        .order_by('-created_at')
    )
    return Response([_order_to_dict(o) for o in orders])


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def order_detail(request, order_id):
    try:
        order = Order.objects.select_related('plan__product').get(
            id=order_id, user=request.user
        )
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_order_to_dict(order))


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_orders(request):
    orders = (
        Order.objects.all()
        .select_related('user', 'plan__product')
        .order_by('-created_at')
    )
    return Response({
        'count': orders.count(),
        'results': [_order_to_dict(o) for o in orders],
    })