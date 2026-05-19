from django.contrib import admin
from .models import DownloadToken

@admin.register(DownloadToken)
class DownloadTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'license', 'is_used', 'expires_at', 'used_at', 'ip_address')
    list_filter = ('is_used',)
    search_fields = ('user__email', 'token')
    readonly_fields = ('id', 'token', 'created_at', 'used_at')
