# notifications/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
import logging

# Set up logger
logger = logging.getLogger(__name__)

class NotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notification toggles
    email_event_invites = models.BooleanField(default=True)
    email_photo_tags = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_likes = models.BooleanField(default=False)
    email_new_photos = models.BooleanField(default=True)
    email_event_updates = models.BooleanField(default=True)
    email_crew_assignments = models.BooleanField(default=True)
    
    # In-app notification toggles
    app_event_invites = models.BooleanField(default=True)
    app_photo_tags = models.BooleanField(default=True)
    app_comments = models.BooleanField(default=True)
    app_likes = models.BooleanField(default=True)
    app_new_photos = models.BooleanField(default=True)
    app_event_updates = models.BooleanField(default=True)
    app_crew_assignments = models.BooleanField(default=True)
    
    # Digest options
    receive_daily_digest = models.BooleanField(default=False)
    receive_weekly_digest = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Preferences for {self.user.username}"

class Notification(models.Model):
    """Individual notification instances"""
    NOTIFICATION_TYPES = (
        ('event_invite', 'Event Invitation'),
        ('photo_tag', 'Photo Tag'),
        ('comment', 'New Comment'),
        ('like', 'New Like'),
        ('new_photo', 'New Photo'),
        ('event_update', 'Event Update'),
        ('crew_assignment', 'Crew Assignment'),
        ('face_recognized', 'Face Recognized'),
        ('access_request', 'Access Request'),
        ('request_approved', 'Request Approved'),
        ('system', 'System Notification'),
    )
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  related_name='sent_notifications', null=True, blank=True)
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # For linking to specific objects (Event, Photo, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Direct URL for the notification target - simplifies template usage
    action_url = models.CharField(max_length=255, blank=True, null=True)
    
    is_read = models.BooleanField(default=False)
    is_email_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}: {self.title}"
    
    def get_icon_class(self):
        """Return the appropriate icon class based on notification type"""
        icon_map = {
            'event_invite': 'fa-calendar-plus',
            'photo_tag': 'fa-tag',
            'comment': 'fa-comment',
            'like': 'fa-heart',
            'new_photo': 'fa-image',
            'event_update': 'fa-calendar-alt',
            'crew_assignment': 'fa-users',
            'face_recognized': 'fa-user-check',
            'access_request': 'fa-unlock-alt',
            'request_approved': 'fa-check-circle',
            'system': 'fa-bell',
        }
        return icon_map.get(self.notification_type, 'fa-bell')
        
    def get_absolute_url(self):
        """Return the URL for the notification's target"""
        try:
            # First check if we have a direct action URL
            if self.action_url and self.action_url.strip():
                return self.action_url
            
            # If no content object, return to notifications list
            if self.content_object is None:
                logger.debug(f"No content object for notification {self.id}")
                return reverse('notifications:list')
                
            # Get the content type model name
            model_name = self.content_type.model
            logger.debug(f"Content type model name: {model_name}")
            
            # For EventPhoto or Photo objects
            if model_name == 'eventphoto' or model_name == 'photo':
                return reverse('photos:photo_detail', kwargs={'pk': self.object_id})
                
            # For Event objects
            elif model_name == 'event':
                # Try to get the slug first
                if hasattr(self.content_object, 'slug') and self.content_object.slug:
                    return reverse('events:event_dashboard', kwargs={'slug': self.content_object.slug})
                else:
                    return reverse('events:event_dashboard', kwargs={'pk': self.object_id})
                    
            # For PhotoComment objects
            elif model_name == 'photocomment':
                return reverse('photos:photo_detail', kwargs={'pk': self.content_object.photo.id})
                    
            # For PhotoLike objects
            elif model_name == 'photolike':
                return reverse('photos:photo_detail', kwargs={'pk': self.content_object.photo.id})
                    
            # For UserPhotoMatch objects
            elif model_name == 'userphotomatch':
                return reverse('photos:photo_detail', kwargs={'pk': self.content_object.photo.id})
                    
            # For EventAccessRequest objects
            elif model_name == 'eventaccessrequest':
                if self.notification_type == 'request_approved':
                    event = self.content_object.event
                    if hasattr(event, 'slug') and event.slug:
                        return reverse('events:event_dashboard', kwargs={'slug': event.slug})
                    else:
                        return reverse('events:event_dashboard', kwargs={'pk': event.id})
                else:
                    return reverse('events:access_requests', kwargs={'pk': self.content_object.event.id})
                    
            # Fall back to content_object's method if it exists
            elif hasattr(self.content_object, 'get_absolute_url'):
                return self.content_object.get_absolute_url()
        except Exception as e:
            # Log the error properly
            logger.error(f"Error in get_absolute_url for notification {self.id}: {e}")
            logger.error(traceback.format_exc())
            return reverse('notifications:list')
        
        # Default fallback
        logger.debug(f"Using default fallback URL for notification {self.id}")
        return reverse('notifications:list')

class EmailLog(models.Model):
    """Track email deliveries"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='email_logs', null=True, blank=True)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='sent')
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Email to {self.recipient_email}: {self.subject}"