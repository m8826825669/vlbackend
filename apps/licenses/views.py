"""
Licenses views — list / fetch licenses, validate keys from desktop app,
manage device activations.

Contract aligned with frontend/src/lib/api.ts.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils import timezone

from .models import License, LicenseActivation


# ─── Serializer helpers ─────────────────────────────────────────────────────
def _license_to_dict(lic, request=None):
    return {
        'id': str(lic.id),
        'license_key': lic.license_key,
        'product_id': str(lic.product.id),
        'product_name': lic.product.name,
        'product_slug': lic.product.slug,
        'product_emoji': lic.product.emoji,
        'plan_id': str(lic.plan.id),
        'plan_name': lic.plan.name,
        'user_email': lic.user.email,
        'user_name': lic.user.get_full_name() or lic.user.email,
        'is_active': lic.is_active,
        'is_expired': lic.is_expired,
        'is_valid': lic.is_valid,
        'max_activations': lic.max_activations,
        'activation_count': lic.activation_count,
        'download_count': lic.download_count,
        'expires_at': lic.expires_at.isoformat() if lic.expires_at else None,
        'created_at': lic.created_at.isoformat(),
        'offline_grace_days': 30,  # surfaced for UI; matches EULA §8
    }


def _activation_to_dict(a):
    return {
        'id': str(a.id),
        'license_id': str(a.license_id),
        'machine_id': a.machine_id,
        'machine_name': a.machine_name or 'Unknown device',
        'device_name': a.machine_name or 'Unknown device',  # alias for frontend
        'os_info': a.os_info,
        'ip_address': a.ip_address,
        'is_active': a.is_active,
        'activated_at': a.activated_at.isoformat(),
        'last_seen': a.last_seen.isoformat(),
    }


# ─── LIST: my licenses ──────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_licenses(request):
    licenses = (
        License.objects.filter(user=request.user)
        .select_related('product', 'plan')
        .order_by('-created_at')
    )
    return Response([_license_to_dict(l) for l in licenses])


# ─── DETAIL ─────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def license_detail(request, license_id):
    try:
        lic = (
            License.objects.select_related('product', 'plan', 'order')
            .get(id=license_id, user=request.user)
        )
    except License.DoesNotExist:
        return Response({'detail': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(_license_to_dict(lic, request))


# ─── ACTIVATIONS LIST ───────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def license_activations(request, license_id):
    """List all activations (devices) for a license owned by the current user."""
    try:
        lic = License.objects.get(id=license_id, user=request.user)
    except License.DoesNotExist:
        return Response({'detail': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

    activations = LicenseActivation.objects.filter(license=lic).order_by('-activated_at')
    return Response([_activation_to_dict(a) for a in activations])


# ─── DEACTIVATE A DEVICE ────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deactivate_machine(request, license_id):
    """
    Free up an activation slot.

    Accepts EITHER:
      {"activation_id": "<uuid>"}     ← frontend sends this
      {"machine_id":    "<string>"}   ← desktop app may send this
    """
    activation_id = request.data.get('activation_id')
    machine_id    = request.data.get('machine_id')

    if not activation_id and not machine_id:
        return Response(
            {'detail': 'Either activation_id or machine_id is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        lic = License.objects.get(id=license_id, user=request.user)
    except License.DoesNotExist:
        return Response({'detail': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        if activation_id:
            activation = LicenseActivation.objects.get(id=activation_id, license=lic)
        else:
            activation = LicenseActivation.objects.get(license=lic, machine_id=machine_id)
    except LicenseActivation.DoesNotExist:
        return Response(
            {'detail': 'No matching activation found for this license.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    activation.delete()
    if lic.activation_count > 0:
        lic.activation_count -= 1
        lic.save(update_fields=['activation_count', 'updated_at'])

    return Response({
        'detail': 'Device deactivated successfully.',
        'remaining_slots': max(0, lic.max_activations - lic.activation_count),
    })


# ─── VALIDATE (called by desktop app, public) ───────────────────────────────
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_license(request):
    """
    Called by the desktop installer/app to validate or activate a key.
    Public endpoint — does NOT require user auth.

    Body: {license_key, machine_id, machine_name?, os_info?}
    """
    key = request.data.get('license_key', '').strip().upper()
    machine_id = request.data.get('machine_id', '').strip()

    if not key or not machine_id:
        return Response({'valid': False, 'error': 'license_key and machine_id are required.'})

    try:
        lic = License.objects.select_related('product', 'plan', 'user').get(license_key=key)
    except License.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid license key.'})

    if not lic.is_active:
        return Response({'valid': False, 'error': 'This license has been deactivated.'})

    if lic.is_expired:
        return Response({'valid': False, 'error': 'This license has expired.'})

    activation, created = LicenseActivation.objects.get_or_create(
        license=lic, machine_id=machine_id,
        defaults={
            'machine_name': request.data.get('machine_name', '')[:200],
            'os_info': request.data.get('os_info', '')[:200],
            'ip_address': request.META.get('REMOTE_ADDR'),
        },
    )

    if created:
        if lic.activation_count >= lic.max_activations:
            activation.delete()
            return Response({
                'valid': False,
                'error': f'Maximum activations ({lic.max_activations}) reached. '
                         f'Deactivate a device from your dashboard to free a slot.',
            })
        lic.activation_count += 1
        lic.save(update_fields=['activation_count', 'updated_at'])
    elif not activation.is_active:
        return Response({'valid': False, 'error': 'This device has been deactivated.'})
    else:
        # Touch last_seen
        activation.save(update_fields=['last_seen'])

    return Response({
        'valid': True,
        'product': lic.product.name,
        'product_slug': lic.product.slug,
        'plan': lic.plan.name,
        'user': lic.user.email,
        'expires_at': lic.expires_at.isoformat() if lic.expires_at else None,
        'offline_grace_days': 30,
    })


# ─── ADMIN ──────────────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_licenses(request):
    licenses = (
        License.objects.all()
        .select_related('user', 'product', 'plan')
        .order_by('-created_at')
    )
    return Response({
        'count': licenses.count(),
        'results': [_license_to_dict(l) for l in licenses],
    })
