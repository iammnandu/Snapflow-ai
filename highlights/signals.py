from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from events.models import Event
from photos.models import EventPhoto
from .tasks import process_new_photo, update_event_best_shots, find_duplicate_photos

@receiver(post_save, sender=EventPhoto)
def photo_post_save(sender, instance, created, **kwargs):
    """
    Signal handler for when a photo is saved.
    This ensures that both new and updated photos are processed.
    """
    if instance.image:
        process_new_photo.delay(instance.id)

@receiver(post_delete, sender=EventPhoto)
def photo_post_delete(sender, instance, **kwargs):
    """
    Signal handler for when a photo is deleted.
    This ensures that best shots and duplicates are recalculated.
    """
    if instance.event_id:
        update_event_best_shots.delay(instance.event_id)
        find_duplicate_photos.delay(instance.event_id)

# Make sure to connect these signals in your app's ready method
def ready():
    post_save.connect(photo_post_save, sender=EventPhoto)
    post_delete.connect(photo_post_delete, sender=EventPhoto)



# signals.py - Make sure signals are connected properly
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import AppConfig

class HighlightsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'highlights'

    def ready(self):
        from events.models import Event
        from photos.models import EventPhoto
        from .signals import photo_post_save, photo_post_delete
        
        post_save.connect(photo_post_save, sender=EventPhoto)
        post_delete.connect(photo_post_delete, sender=EventPhoto)