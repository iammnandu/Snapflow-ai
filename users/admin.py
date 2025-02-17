# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser
from .forms import BasicRegistrationForm

class CustomUserAdmin(UserAdmin):
    add_form = BasicRegistrationForm
    model = CustomUser
    
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff', 'display_avatar')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    def display_avatar(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.avatar.url)
        return "No Avatar"
    display_avatar.short_description = 'Avatar'

    # Different fieldsets for different roles
    base_fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'avatar')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    organizer_fieldsets = (
        ('Organizer Details', {
            'fields': ('company_name', 'website'),
        }),
    )

    photographer_fieldsets = (
        ('Photographer Details', {
            'fields': ('portfolio_url', 'photographer_role', 'watermark'),
        }),
    )

    participant_fieldsets = (
        ('Participant Details', {
            'fields': ('participant_type', 'image_visibility', 'blur_requested', 'remove_requested'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:  # This is an add form
            return self.add_fieldsets

        # Start with base fieldsets
        fieldsets = list(self.base_fieldsets)
        
        # Add role field
        fieldsets.insert(1, ('Role', {'fields': ('role',)}))
        
        # Add role-specific fields
        if obj.role == CustomUser.Roles.ORGANIZER:
            fieldsets.extend(self.organizer_fieldsets)
        elif obj.role == CustomUser.Roles.PHOTOGRAPHER:
            fieldsets.extend(self.photographer_fieldsets)
        elif obj.role == CustomUser.Roles.PARTICIPANT:
            fieldsets.extend(self.participant_fieldsets)
            
        return fieldsets

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # This is an edit
            return ('role',)  # Make role read-only after creation
        return ()

admin.site.register(CustomUser, CustomUserAdmin)