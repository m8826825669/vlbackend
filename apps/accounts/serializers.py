from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name',
                  'phone', 'company', 'password', 'password2')

    def validate(self, attrs):
        # password2 is optional — if provided, must match
        pw2 = attrs.get('password2')
        if pw2 and attrs['password'] != pw2:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def validate_username(self, value):
        if not value:
            # Auto-generate from email if not provided
            return value
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already taken.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        validated_data.pop('password2', None)
        password = validated_data.pop('password')
        # Auto-fill username from email local-part if missing
        if not validated_data.get('username'):
            base = validated_data['email'].split('@')[0]
            candidate = base
            i = 1
            while User.objects.filter(username=candidate).exists():
                i += 1
                candidate = f'{base}{i}'
            validated_data['username'] = candidate
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'].lower(), password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        if not user.is_active:
            raise serializers.ValidationError('Account is disabled. Contact support.')
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'full_name', 'phone', 'company', 'avatar', 'is_verified',
                  'is_staff', 'created_at')
        read_only_fields = ('id', 'email', 'is_staff', 'is_verified', 'created_at')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Accepts payloads from the Next.js reset-password page which sends both
    `uid` and `token` (from the email link), plus the new password under
    either `password` or `new_password`.
    """
    uid = serializers.CharField(required=False, allow_blank=True)
    token = serializers.CharField()
    password = serializers.CharField(required=False, validators=[validate_password])
    new_password = serializers.CharField(required=False, validators=[validate_password])

    def validate(self, attrs):
        pw = attrs.get('password') or attrs.get('new_password')
        if not pw:
            raise serializers.ValidationError({'password': 'New password is required.'})
        attrs['password'] = pw
        return attrs
