# notifications/services.py
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Notification, NotificationPreference, EmailLog
import traceback
import logging

# Set up logger
logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(recipient, notification_type, title, message, related_object=None, from_user=None, action_url=None, send_now=True):
        """Create a notification and optionally send it immediately"""
        try:
            # Validate notification type
            valid_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]
            
            if notification_type not in valid_types:
                logger.error(f"Invalid notification type: {notification_type}")
                logger.error(f"Valid types are: {valid_types}")
                return None
            
            # Create notification object
            notification = Notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                from_user=from_user,
                action_url=action_url
            )
            
            # Link to related object if provided
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                notification.content_type = content_type
                notification.object_id = related_object.id
            
            # Save the notification
            notification.save()
            
            # Send notification immediately if requested
            if send_now:
                NotificationService.send_notification(notification)
            
            logger.info(f"Created notification ID: {notification.id} for {recipient.username}")
            return notification
        except Exception as e:
            logger.error(f"ERROR creating notification: {e}")
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
            try:
                from .tasks import send_notification_email
                # Use Celery task for sending emails asynchronously
                send_notification_email.delay(notification.id)
                logger.info(f"Queued email notification ID: {notification.id} for {recipient.username}")
            except Exception as e:
                logger.error(f"Error queueing email notification: {e}")
                # Fallback to synchronous email
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
            'sender': notification.from_user,  # Include sender in context for email templates
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
                body=plain_message,
                status='sent'
            )
            
            # Update notification
            notification.is_email_sent = True
            notification.save(update_fields=['is_email_sent'])
            
            logger.info(f"Email sent for notification ID: {notification.id}")
            
        except Exception as e:
            logger.error(f"Error sending email for notification ID: {notification.id}: {e}")
            # Log error
            EmailLog.objects.create(
                notification=notification,
                recipient_email=recipient.email,
                subject=notification.title,
                body=str(e),
                status='error',
                error_message=str(e)
            )
    
    @staticmethod
    def mark_as_read(notification_id):
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            logger.info(f"Marked notification ID: {notification_id} as read")
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notification ID: {notification_id} not found")
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read for a user"""
        count = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        logger.info(f"Marked {count} notifications as read for user: {user.username}")
        return count  # Return the count of updated notifications
    
    @staticmethod
    def _send_digest_email(user_id, notifications, digest_type):
        """Send digest email for a collection of notifications"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=user_id)
            
            # Prepare email content
            context = {
                'user': user,
                'notifications': notifications,
                'digest_type': digest_type,
                'site_name': 'SnapFlow',
                'site_url': settings.SITE_URL,
            }
            
            # Get appropriate email template
            template_name = f'notifications/emails/{digest_type}_digest.html'
            
            # Render HTML email
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Send email
            subject = f"Your {digest_type.capitalize()} SnapFlow Digest"
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            # Log email
            EmailLog.objects.create(
                notification=None,  # No specific notification for digests
                recipient_email=user.email,
                subject=subject,
                body=plain_message,
                status='sent'
            )
            
            logger.info(f"Sent {digest_type} digest email to user ID: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending {digest_type} digest email to user ID: {user_id}: {e}")
            traceback.print_exc()
            return False