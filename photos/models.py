# models.py (updated)
import os
from django.db import models
from django.conf import settings

def event_photo_path(instance, filename):
    # Convert event title to a URL-friendly format
    event_slug = instance.event.slug
    
    # Generate path: media/events/<event_id>_<event_slug>/photos/<filename>
    return f'events/{instance.event.id}_{event_slug}/photos/{filename}'

class EventPhoto(models.Model):
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=event_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    
    # AI Processing Fields
    processed = models.BooleanField(default=False)
    highlights = models.BooleanField(default=False)
    quality_score = models.FloatField(null=True, blank=True)
    detected_faces = models.JSONField(null=True, blank=True)
    scene_tags = models.JSONField(null=True, blank=True)
    enhanced_image = models.ImageField(upload_to=event_photo_path, null=True, blank=True)
    
    # Engagement metrics
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['processed']),
        ]

    def __str__(self):
        return f"Photo {self.id} from {self.event.title}"

    def delete(self, *args, **kwargs):
        # Delete the image files when the model instance is deleted
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
                
        if self.enhanced_image:
            if os.path.isfile(self.enhanced_image.path):
                os.remove(self.enhanced_image.path)
                
        super().delete(*args, **kwargs)
    
    def get_tags(self):
        """Get formatted tags for display"""
        if not self.scene_tags:
            return []
        return self.scene_tags
    
    def has_enhanced_version(self):
        """Check if an enhanced version exists"""
        return bool(self.enhanced_image)

    def check_privacy(self, user=None):
        """Check if this photo should be hidden due to privacy requests."""
        from privacy.tasks import check_photo_privacy
        return check_photo_privacy(self, user)

class PhotoLike(models.Model):
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('photo', 'user')
        indexes = [
            models.Index(fields=['photo']),
            models.Index(fields=['user']),
        ]
    def __str__(self):
        return f"{self.user.username} liked photo {self.photo.id}"

class PhotoComment(models.Model):
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['photo']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.username} on photo {self.photo.id}"

class UserPhotoMatch(models.Model):
    """Matches users to photos they appear in"""
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='user_matches')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='photo_appearances')
    confidence_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=100, default='deepface')
    class Meta:
        unique_together = ('photo', 'user')
        indexes = [
            models.Index(fields=['photo']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in photo {self.photo.id} ({self.confidence_score}%)"

class UserGallery(models.Model):
    """Gallery of photos where a user appears"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='personal_gallery')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s personal gallery"
    
    def get_photos(self):
        """Get all photos where this user appears"""
        return EventPhoto.objects.filter(user_matches__user=self.user).order_by('-upload_date')
    
    @property
    def photo_count(self):
        return self.get_photos().count()