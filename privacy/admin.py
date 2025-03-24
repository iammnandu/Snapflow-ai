# privacy/admin.py
from django.contrib import admin
from .models import PrivacyRequest, ProcessedPhoto

@admin.register(PrivacyRequest)
class PrivacyRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'request_type', 'status', 'created_at')
    list_filter = ('status', 'request_type', 'event')
    search_fields = ('user__username', 'user__email', 'event__title')
    readonly_fields = ('created_at', 'updated_at', 'processed_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'event', 'request_type', 'reason', 'status')
        }),
        ('Processing Details', {
            'fields': ('processed_at', 'processed_photos_count', 'rejection_reason')
        }),
    )


@admin.register(ProcessedPhoto)
class ProcessedPhotoAdmin(admin.ModelAdmin):
    list_display = ('privacy_request', 'original_photo', 'processing_date')
    list_filter = ('privacy_request__status', 'privacy_request__request_type')
    search_fields = ('privacy_request__user__username', 'original_photo__caption')
    readonly_fields = ('processing_date',)


