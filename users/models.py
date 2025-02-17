# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        ORGANIZER = 'ORGANIZER', _('Event Organizer')
        PHOTOGRAPHER = 'PHOTOGRAPHER', _('Photographer')
        PARTICIPANT = 'PARTICIPANT', _('Event Participant')

    class ParticipantTypes(models.TextChoices):
        GUEST = 'GUEST', _('Guest')
        FAMILY = 'FAMILY', _('Family')
        FRIEND = 'FRIEND', _('Friend')
        WINNER = 'WINNER', _('Winner')
        OTHER = 'OTHER', _('Other')

    class PhotographerRoles(models.TextChoices):
        LEAD = 'LEAD', _('Lead Photographer')
        ASSISTANT = 'ASSISTANT', _('Assistant Photographer')
        SECONDARY = 'SECONDARY', _('Secondary Photographer')

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        null=True,
        blank=False
    )
    
    # Common fields for all users
    avatar = models.ImageField(
        upload_to='user_avatars/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True
    )
    phone_number = models.CharField(max_length=15, blank=True)
    
    # Organizer specific fields
    company_name = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    
    # Photographer specific fields
    portfolio_url = models.URLField(blank=True)
    photographer_role = models.CharField(
        max_length=20,
        choices=PhotographerRoles.choices,
        blank=True
    )
    watermark = models.ImageField(
        upload_to='photographer_watermarks/',
        validators=[FileExtensionValidator(['png'])],
        null=True,
        blank=True
    )
    
    # Participant specific fields
    participant_type = models.CharField(
        max_length=20,
        choices=ParticipantTypes.choices,
        blank=True
    )
    image_visibility = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('PRIVATE', 'Private'),
            ('EVENT_ONLY', 'Event Only')
        ],
        default='PRIVATE'
    )
    blur_requested = models.BooleanField(default=False)
    remove_requested = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"