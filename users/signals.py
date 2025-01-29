from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser, UserPreferences

@receiver(post_save, sender=CustomUser)
def create_user_preferences(sender, instance, created, **kwargs):
    if created:
        UserPreferences.objects.create(user=instance)
        
        # Send welcome email
        if settings.EMAIL_HOST:
            send_mail(
                'Welcome to SnapFlow',
                f'Hello {instance.username},\n\nWelcome to SnapFlow! Your account has been created successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )