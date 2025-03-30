# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def user_created(sender, instance, created, **kwargs):
    """Handle post-save signals for CustomUser model"""
    if created:
        # Send role-specific welcome email
        if settings.EMAIL_HOST:
            context = {
                'username': instance.username,
                'role': instance.get_role_display(),
            }
            
            # Select email template based on user role
            if instance.role == CustomUser.Roles.ORGANIZER:
                template = 'email/welcome_organizer.html'
            elif instance.role == CustomUser.Roles.PHOTOGRAPHER:
                template = 'email/welcome_photographer.html'
            else:
                template = 'email/welcome_participant.html'
            
            # Render email content from template
            html_message = render_to_string(template, context)
            plain_message = render_to_string(f"{template.replace('.html', '.txt')}", context)
            
            # Send email
            try:
                send_mail(
                    subject=f'Welcome to Event Management - {instance.get_role_display()}',
                    message=plain_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Failed to send welcome email: {str(e)}")

@receiver(post_save, sender=CustomUser)
def user_profile_updated(sender, instance, created, **kwargs):
    """Handle profile updates"""
    if not created and instance.role == CustomUser.Roles.PHOTOGRAPHER:
        # Notify admin about new photographer profile completion
        if instance.portfolio_url and instance.photographer_role and not instance.is_verified:
            try:
                admin_emails = [admin.email for admin in CustomUser.objects.filter(is_superuser=True)]
                if admin_emails:
                    send_mail(
                        subject='New Photographer Profile Needs Verification',
                        message=f'Photographer {instance.username} has completed their profile and needs verification.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=admin_emails,
                        fail_silently=True,
                    )
            except Exception as e:
                print(f"Failed to send admin notification: {str(e)}")
