"""
Accounts views — registration, login, profile, password reset.

Response shape matches what the Next.js frontend store expects:
  login/register return access + refresh AT THE TOP LEVEL (plus user object).
"""
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import secrets
import logging

from .models import User
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
)

logger = logging.getLogger(__name__)


def _auth_response(user, status_code=status.HTTP_200_OK):
    """
    Return tokens at top level (matches frontend store.ts):
        const { data } = await authAPI.login(...)
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)
        set({ user: data.user, ... })
    """
    refresh = RefreshToken.for_user(user)
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': UserSerializer(user).data,
        # Backward-compat: nested copy
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        },
    }, status=status_code)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _auth_response(user, status_code=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _auth_response(serializer.validated_data['user'])


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh = request.data.get('refresh')
            if refresh:
                RefreshToken(refresh).blacklist()
        except Exception:
            pass  # Don't 4xx on logout — client is leaving anyway
        return Response({'detail': 'Logged out successfully.'})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password changed successfully.'})


class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        try:
            user = User.objects.get(email__iexact=email)
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = timezone.now() + timedelta(hours=1)
            user.save(update_fields=['password_reset_token', 'password_reset_expires', 'updated_at'])

            # Frontend reset page reads ?uid=<id>&token=<token>
            reset_url = f'{settings.SITE_URL}/auth/reset-password?uid={user.id}&token={token}'

            try:
                from apps.orders.email_utils import send_password_reset_email
                send_password_reset_email(user, reset_url)
            except Exception:
                # Fallback to plain text
                send_mail(
                    f'Reset your {settings.SITE_NAME} password',
                    f'Click to reset your password (expires in 1 hour):\n\n{reset_url}',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
        except User.DoesNotExist:
            pass  # Don't reveal whether the email exists
        return Response({'detail': 'If this email is registered, a reset link has been sent.'})


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['password']
        uid = serializer.validated_data.get('uid')

        # Look up by token AND (optionally) uid for extra safety
        qs = User.objects.filter(
            password_reset_token=token,
            password_reset_expires__gt=timezone.now(),
        )
        if uid:
            qs = qs.filter(id=uid)

        try:
            user = qs.get()
        except (User.DoesNotExist, ValueError):
            return Response(
                {'detail': 'This reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.password_reset_token = ''
        user.password_reset_expires = None
        user.save()
        return Response({'detail': 'Password has been reset. You can now sign in.'})


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def admin_users_list(request):
    users = User.objects.all().order_by('-created_at')
    return Response({
        'count': users.count(),
        'results': UserSerializer(users, many=True).data,
    })
