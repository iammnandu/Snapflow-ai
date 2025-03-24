# privacy/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from events.models import Event
from photos.models import EventPhoto

class PrivacyRequest(models.Model):
    """Model to store privacy requests from participants."""
    
    REQUEST_TYPES = (
        ('blur', _('Blur my face')),
        ('hide', _('Hide photos with me')),
    )
    
    STATUS_CHOICES = (
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='privacy_requests'
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='privacy_requests'
    )
    request_type = models.CharField(
        max_length=10,
        choices=REQUEST_TYPES,
        default='blur'
    )
    reason = models.TextField(
        blank=True,
        help_text=_('Optional reason for the privacy request')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Processed details
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_photos_count = models.PositiveIntegerField(default=0)
    
    # For reject reason
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('user', 'event', 'request_type')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_request_type_display()} request by {self.user.username} for {self.event.title}"
    
    def get_absolute_url(self):
        return reverse('privacy:request_detail', kwargs={'pk': self.pk})


class ProcessedPhoto(models.Model):
    """Model to track processed photos for privacy requests."""
    
    privacy_request = models.ForeignKey(
        PrivacyRequest,
        on_delete=models.CASCADE,
        related_name='processed_photos'
    )
    original_photo = models.ForeignKey(
        EventPhoto,
        on_delete=models.CASCADE,
        related_name='privacy_versions'
    )
    processed_image = models.ImageField(
        upload_to='privacy_processed/%Y/%m/',
        blank=True,
        null=True
    )
    processing_date = models.DateTimeField(auto_now_add=True)
    
    # For blur requests, we store the face coordinates that were blurred
    face_coordinates = models.JSONField(null=True, blank=True)
    
    class Meta:
        unique_together = ('privacy_request', 'original_photo')
    
    def __str__(self):
        return f"Processed photo {self.original_photo.id} for {self.privacy_request}"