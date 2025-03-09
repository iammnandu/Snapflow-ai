# notifications/services.py
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification, NotificationPreference, EmailLog
import traceback

# notifications/services.py
from django.db import transaction

# notifications/services.py
class NotificationService:
    @staticmethod
    def create_notification(recipient, notification_type, title, message, related_object=None, send_now=True):
        """Create a notification and optionally send it immediately"""
        try:
            print(f"Creating notification for {recipient.username} of type {notification_type}")
            
            # Validate notification type
            from .models import Notification
            valid_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]

            if notification_type not in valid_types:
                print(f"Invalid notification type: {notification_type}")
                print(f"Valid types are: {valid_types}")
                return None
            
            # Create notification object
            notification = Notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message
            )
            
            # Validate model fields
            try:
                notification.full_clean()
            except Exception as validation_error:
                print(f"Validation error: {validation_error}")
                return None
                
            # Link to related object if provided
            if related_object:
                from django.contrib.contenttypes.models import ContentType
                content_type = ContentType.objects.get_for_model(related_object)
                notification.content_type = content_type
                notification.object_id = related_object.id
            
            # Save the notification
            notification.save()
            print(f"Notification created with ID: {notification.id}")
            
            # Send notification immediately if requested
            if send_now:
                NotificationService.send_notification(notification)
            
            return notification
            
        except Exception as e:
            print(f"ERROR creating notification: {e}")
            import traceback
            traceback.print_exc()
            return None
        

    @staticmethod
    def send_notification(notification):
        """Send a notification via the appropriate channels"""
        recipient = notification.recipient
        
        # Get user preferences (create if doesn't exist)
        preferences, created = NotificationPreference.objects.get_or_create(user=recipient)
        
        # Determine if we should send email based on notification type and user preferences
        send_email = False
        
        if notification.notification_type == 'event_invite' and preferences.email_event_invites:
            send_email = True
        elif notification.notification_type == 'photo_tag' and preferences.email_photo_tags:
            send_email = True
        elif notification.notification_type == 'comment' and preferences.email_comments:
            send_email = True
        elif notification.notification_type == 'like' and preferences.email_likes:
            send_email = True
        elif notification.notification_type == 'new_photo' and preferences.email_new_photos:
            send_email = True
        elif notification.notification_type == 'event_update' and preferences.email_event_updates:
            send_email = True
        elif notification.notification_type == 'crew_assignment' and preferences.email_crew_assignments:
            send_email = True
        elif notification.notification_type in ['face_recognized', 'access_request', 'request_approved', 'system']:
            # Always send emails for important system notifications
            send_email = True
        
        # Send email if needed
        if send_email and recipient.email:
            NotificationService._send_email_notification(notification)
    
    @staticmethod
    def _send_email_notification(notification):
        """Send email for a notification"""
        recipient = notification.recipient
        
        # Prepare email content
        context = {
            'user': recipient,
            'notification': notification,
            'site_name': 'SnapFlow',
            'site_url': settings.SITE_URL,
        }
        
        # Get appropriate email template based on notification type
        template_name = f'notifications/emails/{notification.notification_type}.html'
        
        try:
            # Render HTML email
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Send email
            send_mail(
                subject=notification.title,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Log email
            EmailLog.objects.create(
                notification=notification,
                recipient_email=recipient.email,
                subject=notification.title,
                body=plain_message
            )
            
            # Update notification
            notification.is_email_sent = True
            notification.save(update_fields=['is_email_sent'])
            
        except Exception as e:
            # Log error
            EmailLog.objects.create(
                notification=notification,
                recipient_email=recipient.email,
                subject=notification.title,
                body=str(e),
                status='error'
            )
    
    @staticmethod
    def mark_as_read(notification_id):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read for a user"""
        Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)