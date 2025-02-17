# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .forms import BaseRegistrationForm, ProfileUpdateForm

class CustomUserAdmin(UserAdmin):
    add_form = BaseRegistrationForm
    form = ProfileUpdateForm
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    
    # Define different fieldsets for different user roles
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'avatar')}),
        ('Role', {'fields': ('role',)}),
        ('Organizer Fields', {
            'classes': ('collapse',),
            'fields': ('company_name', 'website'),
        }),
        ('Photographer Fields', {
            'classes': ('collapse',),
            'fields': ('portfolio_url', 'photographer_role', 'watermark'),
        }),
        ('Participant Fields', {
            'classes': ('collapse',),
            'fields': ('participant_type', 'image_visibility', 'blur_requested', 'remove_requested'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:  # This is an edit
            # Remove irrelevant fieldsets based on user role
            if obj.role == CustomUser.Roles.ORGANIZER:
                fieldsets = [fs for fs in fieldsets if 'Photographer Fields' not in fs and 'Participant Fields' not in fs]
            elif obj.role == CustomUser.Roles.PHOTOGRAPHER:
                fieldsets = [fs for fs in fieldsets if 'Organizer Fields' not in fs and 'Participant Fields' not in fs]
            elif obj.role == CustomUser.Roles.PARTICIPANT:
                fieldsets = [fs for fs in fieldsets if 'Organizer Fields' not in fs and 'Photographer Fields' not in fs]
        return fieldsets

    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)