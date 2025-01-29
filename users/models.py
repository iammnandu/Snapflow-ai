from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        CLIENT = 'CLIENT', _('Client')
        EVENT_CREW = 'EVENT_CREW', _('Event Crew')
        PHOTOGRAPHER = 'PHOTOGRAPHER', _('Photographer')
        EVENT_PARTICIPANT = 'EVENT_PARTICIPANT', _('Event Participant')
        GENERAL_USER = 'GENERAL_USER', _('General User')

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.GENERAL_USER
    )
    avatar = models.ImageField(
        upload_to='user_avatars/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )
    bio = models.TextField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    company_name = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    gdpr_consent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    
    # Photographer specific fields
    portfolio_url = models.URLField(blank=True)
    equipment_details = models.TextField(blank=True)
    expertise = models.CharField(max_length=100, blank=True)
    
    # Client specific fields
    organization_type = models.CharField(max_length=50, blank=True)
    billing_address = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class UserPreferences(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    dark_mode = models.BooleanField(default=False)
    language = models.CharField(max_length=10, default='en')
    email_notifications = models.BooleanField(default=True)
    privacy_level = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('PRIVATE', 'Private'),
            ('EVENT_ONLY', 'Event Only')
        ],
        default='PRIVATE'
    )
    auto_face_blur = models.BooleanField(default=False)
