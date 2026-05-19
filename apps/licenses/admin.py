from django.contrib import admin
from .models import License, LicenseActivation

class ActivationInline(admin.TabularInline):
    model = LicenseActivation
    extra = 0
    readonly_fields = ('machine_id', 'machine_name', 'os_info', 'ip_address', 'activated_at', 'last_seen')

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('license_key', 'user', 'product', 'plan', 'is_active', 'activation_count', 'download_count', 'created_at')
    list_filter = ('is_active', 'product')
    search_fields = ('license_key', 'user__email')
    readonly_fields = ('id', 'license_key', 'created_at', 'updated_at')
    inlines = [ActivationInline]
