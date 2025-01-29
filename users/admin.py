from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserPreferences
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('username', 'email', 'role', 'is_staff', 'is_verified')
    list_filter = ('role', 'is_staff', 'is_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'avatar', 'bio', 'phone_number',
                                      'company_name', 'website', 'gdpr_consent')}),
        ('Photographer Info', {'fields': ('portfolio_url', 'equipment_details', 'expertise')}),
        ('Client Info', {'fields': ('organization_type', 'billing_address')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserPreferences)