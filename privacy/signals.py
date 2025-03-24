
# privacy/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PrivacyRequest
from .tasks import process_privacy_request

@receiver(post_save, sender=PrivacyRequest)
def handle_privacy_request(sender, instance, created, **kwargs):
    """Trigger processing when a request is approved."""
    if instance.status == 'approved':
        process_privacy_request.delay(instance.id)