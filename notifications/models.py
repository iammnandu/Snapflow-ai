from django.db import models
from django.utils import timezone
from users.models import CustomUser

class Notification(models.Model):
    """Base notification model."""
    NOTIFICATION_TYPES = (
        ('photo_upload', 'Photo Upload'),
        ('face_recognition', 'Face Recognition'),
        ('comment', 'Comment'),
        ('like', 'Like'),
        ('event_invitation', 'Event Invitation'),
        ('crew_assignment', 'Crew Assignment'),
        ('event_reminder', 'Event Reminder'),
        ('processing_complete', 'Photo Processing Complete'),
        ('access_request', 'Event Access Request'),
        ('access_granted', 'Access Granted'),
        ('system', 'System Notification'),
    )
    
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Reference fields to related objects
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, null=True, blank=True)
    photo = models.ForeignKey('photos.EventPhoto', on_delete=models.CASCADE, null=True, blank=True)
    from_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='sent_notifications')
    
    # Action URL for the notification (where clicking takes the user)
    action_url = models.CharField(max_length=255, null=True, blank=True)
    
    # Notification priority
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Email status (for notifications that also send emails)
    email_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read', 'created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"
    
    def mark_as_read(self):
        self.read = True
        self.read_at = timezone.now()
        self.save()


class NotificationPreference(models.Model):
    """User preferences for notifications."""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notification preferences
    email_photo_upload = models.BooleanField(default=True)
    email_face_recognition = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_likes = models.BooleanField(default=False)
    email_event_invitation = models.BooleanField(default=True)
    email_crew_assignment = models.BooleanField(default=True)
    email_event_reminder = models.BooleanField(default=True)
    
    # In-app notification preferences
    notify_photo_upload = models.BooleanField(default=True)
    notify_face_recognition = models.BooleanField(default=True)
    notify_comments = models.BooleanField(default=True)
    notify_likes = models.BooleanField(default=True)
    notify_event_invitation = models.BooleanField(default=True)
    notify_crew_assignment = models.BooleanField(default=True)
    notify_event_reminder = models.BooleanField(default=True)
    notify_processing_complete = models.BooleanField(default=True)
    
    # Notification digests
    receive_daily_digest = models.BooleanField(default=False)
    receive_weekly_digest = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification preferences for {self.user.username}"