from django.db import models
from django.conf import settings
from django.utils.text import slugify
import os

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
    quality_score = models.FloatField(null=True, blank=True)
    detected_faces = models.JSONField(null=True, blank=True)
    scene_tags = models.JSONField(null=True, blank=True)
    
    # Engagement metrics
    view_count = models.IntegerField(default=0)
    like_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return f"Photo {self.id} from {self.event.title}"

    def delete(self, *args, **kwargs):
        # Delete the image file when the model instance is deleted
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)

class PhotoLike(models.Model):
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['photo', 'user']

class PhotoComment(models.Model):
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']