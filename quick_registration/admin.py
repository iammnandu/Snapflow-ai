from django.contrib import admin
from .models import QuickRegistrationLink

@admin.register(QuickRegistrationLink)
class QuickRegistrationLinkAdmin(admin.ModelAdmin):
    list_display = ('event', 'code', 'created_at', 'expires_at', 'is_active')
    list_filter = ('is_active', 'event')
    search_fields = ('code', 'event__title')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event')