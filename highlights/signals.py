# highlights/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from events.models import Event
from photos.models import EventPhoto
from .tasks import process_new_photo, update_event_best_shots, find_duplicate_photos

@receiver(post_save, sender=EventPhoto)
def photo_post_save(sender, instance, created, **kwargs):
    """Signal handler for when a photo is saved."""
    if instance.image:
        process_new_photo.delay(instance.id)

@receiver(post_delete, sender=EventPhoto)
def photo_post_delete(sender, instance, **kwargs):
    """Signal handler for when a photo is deleted."""
    if instance.event_id:
        update_event_best_shots.delay(instance.event_id)
        find_duplicate_photos.delay(instance.event_id)
