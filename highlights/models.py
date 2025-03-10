from django.db import models
from events.models import Event
from photos.models import EventPhoto

class BestShot(models.Model):
    """Model to store the best shots from an event."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='best_shots')
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='best_shot_entries')
    score = models.FloatField(help_text="Quality score determining why this is a best shot")
    category = models.CharField(
        max_length=50, 
        choices=[
            ('OVERALL', 'Overall Quality'),
            ('PORTRAIT', 'Best Portrait'),
            ('GROUP', 'Best Group Shot'),
            ('ACTION', 'Best Action Shot'),
            ('COMPOSITION', 'Best Composition'),
            ('LIGHTING', 'Best Lighting'),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('event', 'category', 'photo')
        ordering = ['-score']
    
    def __str__(self):
        return f"{self.event.title} - {self.get_category_display()} - {self.score}"


class DuplicateGroup(models.Model):
    """Model to group duplicate or similar photos together."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='duplicate_groups')
    similarity_threshold = models.FloatField(default=0.85)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Duplicate Group {self.id} - {self.event.title}"


class DuplicatePhoto(models.Model):
    """Model to store photos that are duplicates or near-duplicates."""
    group = models.ForeignKey(DuplicateGroup, on_delete=models.CASCADE, related_name='photos')
    photo = models.ForeignKey(EventPhoto, on_delete=models.CASCADE, related_name='duplicate_entries')
    is_primary = models.BooleanField(default=False, help_text="Primary (best) photo in the duplicate group")
    similarity_score = models.FloatField(help_text="Similarity score to primary photo")
    
    class Meta:
        unique_together = ('group', 'photo')
        ordering = ['-is_primary', '-similarity_score']
    
    def __str__(self):
        return f"{self.photo.id} - {'Primary' if self.is_primary else 'Duplicate'} - {self.similarity_score}"