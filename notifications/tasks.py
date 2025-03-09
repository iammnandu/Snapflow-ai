# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from photos.models import EventPhoto, PhotoComment, PhotoLike, UserPhotoMatch
from events.models import EventCrew, EventParticipant, EventAccessRequest
from .handlers import NotificationHandler

@receiver(post_save, sender=EventPhoto)
def photo_created(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_photo_upload(instance)

@receiver(post_save, sender=UserPhotoMatch)
def face_recognized(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_face_recognition(instance)

@receiver(post_save, sender=PhotoComment)
def comment_created(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_photo_comment(instance)

@receiver(post_save, sender=PhotoLike)
def like_created(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_photo_like(instance)

@receiver(post_save, sender=EventCrew)
def crew_invited(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_event_invitation(instance)

@receiver(post_save, sender=EventParticipant)
def participant_invited(sender, instance, created, **kwargs):
    if created and instance.user:
        NotificationHandler.handle_participant_invitation(instance)

@receiver(post_save, sender=EventAccessRequest)
def access_requested(sender, instance, created, **kwargs):
    if created:
        NotificationHandler.handle_access_request(instance)

@receiver(post_save, sender=EventAccessRequest)
def request_status_changed(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        NotificationHandler.handle_request_approved(instance)