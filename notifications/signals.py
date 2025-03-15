# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from photos.models import EventPhoto, PhotoComment, PhotoLike, UserPhotoMatch
from events.models import EventCrew, EventParticipant, EventAccessRequest
from .handlers import NotificationHandler
import logging

# Set up logger
logger = logging.getLogger(__name__)

@receiver(post_save, sender=EventPhoto)
def photo_created(sender, instance, created, **kwargs):
    logger.debug(f"Signal received: EventPhoto saved, created={created}")
    if created:
        logger.info(f"Handling photo upload: {instance.id}")
        NotificationHandler.handle_photo_upload(instance)

@receiver(post_save, sender=UserPhotoMatch)
def face_recognized(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Face recognized for user: {instance.user.id} in photo: {instance.photo.id}")
        NotificationHandler.handle_face_recognition(instance)

@receiver(post_save, sender=PhotoComment)
def comment_created(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New comment created by {instance.user.id} on photo: {instance.photo.id}")
        NotificationHandler.handle_photo_comment(instance)

@receiver(post_save, sender=PhotoLike)
def like_created(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New like by {instance.user.id} on photo: {instance.photo.id}")
        NotificationHandler.handle_photo_like(instance)

@receiver(post_save, sender=EventCrew)
def crew_invited(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Crew member {instance.member.id} invited to event: {instance.event.id}")
        NotificationHandler.handle_event_invitation(instance)

@receiver(post_save, sender=EventParticipant)
def participant_invited(sender, instance, created, **kwargs):
    if created and instance.user:
        logger.info(f"Participant {instance.user.id} invited to event: {instance.event.id}")
        NotificationHandler.handle_participant_invitation(instance)

@receiver(post_save, sender=EventAccessRequest)
def access_requested(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Access request by {instance.user.id} for event: {instance.event.id}")
        NotificationHandler.handle_access_request(instance)

@receiver(post_save, sender=EventAccessRequest)
def request_status_changed(sender, instance, created, **kwargs):
    if not created and instance.status == 'approved':
        logger.info(f"Access request approved for {instance.user.id} on event: {instance.event.id}")
        NotificationHandler.handle_request_approved(instance)