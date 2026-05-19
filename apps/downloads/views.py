"""
Downloads — secure, time-limited installer downloads gated by licenses.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions, status
from django.http import FileResponse, Http404
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import os
import logging

from .models import DownloadToken
from apps.licenses.models import License

logger = logging.getLogger(__name__)


def _absolute_url(request, path):
    """Build an absolute URL the frontend can redirect to."""
    if request:
        return request.build_absolute_uri(path)
    return f"{settings.SITE_URL.rstrip('/')}{path}"


# ─── REQUEST A DOWNLOAD (gated by license) ──────────────────────────────────
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def request_download(request):
    """
    Frontend: downloadsAPI.request({ license_id })
    Returns:  { download_url, expires_in_hours, expires_at }
    """
    license_id = request.data.get('license_id')
    if not license_id:
        return Response({'detail': 'license_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        lic = License.objects.select_related('product').get(id=license_id, user=request.user)
    except License.DoesNotExist:
        return Response({'detail': 'License not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not lic.is_valid:
        return Response(
            {'detail': 'This license is not valid or has expired.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not lic.product.installer_file:
        return Response(
            {'detail': 'Installer is not yet available for this product. Our team will email you when it is uploaded.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    max_dl = getattr(settings, 'MAX_DOWNLOADS_PER_LICENSE', 5)
    if lic.download_count >= max_dl:
        return Response(
            {'detail': f'Maximum download attempts ({max_dl}) reached. Contact support to reset.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    expiry_hours = getattr(settings, 'DOWNLOAD_TOKEN_EXPIRY_HOURS', 2)
    token = secrets.token_urlsafe(48)
    dt = DownloadToken.objects.create(
        token=token,
        license=lic,
        user=request.user,
        expires_at=timezone.now() + timedelta(hours=expiry_hours),
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    return Response({
        'download_url': _absolute_url(request, f'/api/downloads/file/{token}/'),
        'expires_in_hours': expiry_hours,
        'expires_at': dt.expires_at.isoformat(),
        'product_name': lic.product.name,
        'file_size': lic.product.file_size or '',
        'version': lic.product.version,
    })


# ─── SERVE THE FILE ─────────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def serve_download(request, token):
    """Validate the token and stream the installer file."""
    try:
        dt = DownloadToken.objects.select_related('license__product', 'user').get(token=token)
    except DownloadToken.DoesNotExist:
        raise Http404('Download link is invalid.')

    if not dt.is_valid:
        return Response(
            {'detail': 'This download link has expired or already been used. Request a new one from your dashboard.'},
            status=status.HTTP_410_GONE,
        )

    product = dt.license.product
    if not product.installer_file:
        return Response(
            {'detail': 'Installer file is not available on the server.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    file_path = product.installer_file.path
    if not os.path.exists(file_path):
        logger.error(f'Installer file missing on disk: {file_path}')
        return Response(
            {'detail': 'Installer file missing on server. Contact support.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Mark token as used + bump license counter
    dt.is_used = True
    dt.used_at = timezone.now()
    dt.save(update_fields=['is_used', 'used_at'])

    lic = dt.license
    lic.download_count += 1
    lic.save(update_fields=['download_count', 'updated_at'])

    filename = os.path.basename(file_path)
    response = FileResponse(
        open(file_path, 'rb'),
        content_type='application/octet-stream',
        as_attachment=True,
        filename=filename,
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    try:
        response['Content-Length'] = os.path.getsize(file_path)
    except OSError:
        pass
    return response


# ─── DOWNLOAD HISTORY ───────────────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_history(request):
    """
    Frontend renders: { product_name | file_name, created_at, download_url? }
    """
    tokens = (
        DownloadToken.objects.filter(user=request.user, is_used=True)
        .select_related('license__product')
        .order_by('-used_at')
    )
    return Response([{
        'id': str(t.id),
        'product_name': t.license.product.name,
        'product_slug': t.license.product.slug,
        'file_name': f'{t.license.product.slug}-{t.license.product.version}.installer',
        'version': t.license.product.version,
        'created_at': (t.used_at or t.created_at).isoformat(),
        'ip_address': t.ip_address,
    } for t in tokens])
