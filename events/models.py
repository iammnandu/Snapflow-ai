#events/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.text import slugify
from django.utils.crypto import get_random_string

class Event(models.Model):
    class EventTypes(models.TextChoices):
        WEDDING = 'WEDDING', _('Wedding')
        BIRTHDAY = 'BIRTHDAY', _('Birthday')
        CORPORATE = 'CORPORATE', _('Corporate Event')
        CULTURAL = 'CULTURAL', _('Cultural Event')
        SPORTS = 'SPORTS', _('Sports Event')
        ACADEMIC = 'ACADEMIC', _('Academic Event')
        AWARD = 'AWARD', _('Award Ceremony')
        PUBLIC = 'PUBLIC', _('Public Gathering')
        OTHER = 'OTHER', _('Other')

    class EventStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    # Basic Event Details
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventTypes.choices,
        default=EventTypes.OTHER
    )
    description = models.TextField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    timezone = models.CharField(max_length=50, default='UTC')
    location = models.CharField(max_length=255)
    event_code = models.CharField(max_length=6, unique=True, blank=True)
    primary_color = models.CharField(max_length=7, default="#ffffff")  # Hex color
    secondary_color = models.CharField(max_length=7, default="#000000")  # Hex color
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT
    )

    # Organizer Details
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )
    
    # Event Website Customization
    custom_domain = models.CharField(max_length=255, blank=True)
    theme = models.ForeignKey(
        'EventTheme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    logo = models.ImageField(upload_to='event_logos/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='event_covers/', null=True, blank=True)
    
    # Privacy Settings
    is_public = models.BooleanField(default=False)
    require_registration = models.BooleanField(default=True)
    allow_guest_upload = models.BooleanField(default=False)
    
    # AI Features
    enable_face_detection = models.BooleanField(default=True)
    enable_moment_detection = models.BooleanField(default=True)
    enable_auto_tagging = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.title


    def save(self, *args, **kwargs):
        # Generate slug if not present
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Generate unique event code if not present
        if not self.event_code:
            while True:
                code = get_random_string(6).upper()
                if not Event.objects.filter(event_code=code).exists():
                    self.event_code = code
                    break
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('events:event_dashboard', kwargs={'slug': self.slug})

class EventTheme(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    template = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='theme_thumbnails/')
    is_active = models.BooleanField(default=True)
    
    # Theme Settings
    primary_color = models.CharField(max_length=7, default='#000000')
    secondary_color = models.CharField(max_length=7, default='#ffffff')
    font_family = models.CharField(max_length=100, default='Arial')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class EventCrew(models.Model):
    class CrewRoles(models.TextChoices):
        LEAD = 'LEAD', _('Lead Photographer')
        SECOND = 'SECOND', _('Second Photographer')
        ASSISTANT = 'ASSISTANT', _('Assistant')
        VIDEOGRAPHER = 'VIDEO', _('Videographer')
        EDITOR = 'EDITOR', _('Photo Editor')
        OTHER = 'OTHER', _('Other')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='crew_members')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=CrewRoles.choices)
    is_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    equipment = models.TextField(blank=True)
    assigned_area = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['event', 'member']

    def __str__(self):
        return f"{self.member.username} - {self.get_role_display()} at {self.event.title}"

class EventParticipant(models.Model):
    class ParticipantTypes(models.TextChoices):
        GUEST = 'GUEST', _('Guest')
        VIP = 'VIP', _('VIP')
        SPEAKER = 'SPEAKER', _('Speaker')
        PERFORMER = 'PERFORMER', _('Performer')
        STAFF = 'STAFF', _('Staff')
        OTHER = 'OTHER', _('Other')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    email = models.EmailField()
    name = models.CharField(max_length=100)
    participant_type = models.CharField(
        max_length=20,
        choices=ParticipantTypes.choices,
        default=ParticipantTypes.GUEST
    )
    is_registered = models.BooleanField(default=False)
    registration_code = models.CharField(max_length=20, unique=True)
    
    # Privacy Settings
    allow_photos = models.BooleanField(default=True)
    request_blur = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['event', 'email']

    def __str__(self):
        return f"{self.name} at {self.event.title}"

class EventConfiguration(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='configuration')
    
    # Gallery Settings
    enable_comments = models.BooleanField(default=True)
    enable_likes = models.BooleanField(default=True)
    enable_download = models.BooleanField(default=False)
    download_watermark = models.BooleanField(default=True)
    
    # Upload Settings
    max_upload_size = models.IntegerField(default=10485760)  # 10MB
    allowed_formats = models.CharField(
        max_length=200,
        default='jpg,jpeg,png,heic'
    )
    
    # AI Processing
    enable_face_grouping = models.BooleanField(default=True)
    enable_scene_detection = models.BooleanField(default=True)
    enable_quality_filter = models.BooleanField(default=True)
    
    # Notification Settings
    notify_on_upload = models.BooleanField(default=True)
    notify_on_comment = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuration for {self.event.title}"
    


class EventAccessRequest(models.Model):
    class RequestStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='access_requests')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=[
        ('PHOTOGRAPHER', 'Photographer'),
        ('PARTICIPANT', 'Participant')
    ])
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['event', 'user']