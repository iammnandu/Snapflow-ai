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
        email_priority = 2  # Default medium priority
        
        if notification.notification_type == 'event_invite' and preferences.email_event_invites:
            send_email = True
            email_priority = 3  # High priority
        elif notification.notification_type == 'photo_tag' and preferences.email_photo_tags:
            send_email = True
            email_priority = 2  # Medium priority
        elif notification.notification_type == 'comment' and preferences.email_comments:
            send_email = True
            email_priority = 1  # Low priority
        elif notification.notification_type == 'like' and preferences.email_likes:
            send_email = True
            email_priority = 1  # Low priority
        elif notification.notification_type == 'new_photo' and preferences.email_new_photos:
            send_email = True
            email_priority = 2  # Medium priority
        elif notification.notification_type == 'event_update' and preferences.email_event_updates:
            send_email = True
            email_priority = 2  # Medium priority
        elif notification.notification_type == 'crew_assignment' and preferences.email_crew_assignments:
            send_email = True
            email_priority = 3  # High priority
        elif notification.notification_type in ['face_recognized']:
            send_email = True
            email_priority = 3  # High priority
        elif notification.notification_type in ['access_request', 'request_approved', 'system']:
            # Always send emails for important system notifications
            send_email = True
            email_priority = 4  # Critical priority - send immediately
        
        # Send email if needed
        if send_email and recipient.email:
            try:
                # Critical notifications (priority 4) always send immediately
                if email_priority >= 4:
                    from .tasks import send_notification_email
                    # Use Celery task for sending emails asynchronously
                    send_notification_email.delay(notification.id)
                    logger.info(f"Queued immediate email notification ID: {notification.id} for {recipient.username}")
                else:
                    # Queue non-critical notifications for batch processing
                    from .models import PendingEmailNotification
                    PendingEmailNotification.objects.create(
                        notification=notification,
                        priority=email_priority
                    )
                    logger.info(f"Queued batch email notification ID: {notification.id} for {recipient.username}")
            except Exception as e:
                logger.error(f"Error queueing email notification: {e}")
                # Fallback to synchronous email for critical notifications only
                if email_priority >= 4:
                    NotificationService._send_email_notification(notification)
    
    @staticmethod
    def process_email_batches(batch_time):
        """Process pending email notifications for the specified batch time (morning/evening)"""
        from .models import PendingEmailNotification
        from django.utils import timezone
        from django.db.models import Count
        
        try:
            # Get all pending notifications grouped by recipient
            pending_by_user = PendingEmailNotification.objects.values('notification__recipient').annotate(
                count=Count('id')
            ).order_by('notification__recipient')
            
            for user_data in pending_by_user:
                recipient_id = user_data['notification__recipient']
                count = user_data['count']
                
                # Get this user's pending notifications
                user_notifications = PendingEmailNotification.objects.filter(
                    notification__recipient_id=recipient_id
                ).select_related('notification')
                
                # Process notifications based on user's preferences and notification priority
                NotificationService._send_batch_email(recipient_id, user_notifications, batch_time)
                
            logger.info(f"Completed {batch_time} email batch processing")
            return True
        except Exception as e:
            logger.error(f"Error processing {batch_time} email batches: {e}")
            traceback.print_exc()
            return False
    
    @staticmethod
    def _send_batch_email(user_id, pending_notifications, batch_time):
        """Send a single digest email for multiple notifications"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            # Get the user
            user = User.objects.get(id=user_id)
            
            # Get actual notification objects
            notifications = [pn.notification for pn in pending_notifications]
            
            if not notifications:
                return False
                
            # Group notifications by type for better readability
            notification_groups = {}
            for notification in notifications:
                group = notification.get_notification_type_display()
                if group not in notification_groups:
                    notification_groups[group] = []
                notification_groups[group].append(notification)
            
            # Prepare email content
            context = {
                'user': user,
                'notifications': notifications,
                'notification_groups': notification_groups,
                'batch_time': batch_time,
                'site_name': 'SnapFlow',
                'site_url': settings.SITE_URL,
            }
            
            # Render HTML email
            template_name = 'notifications/emails/batch_digest.html'
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)
            
            # Send email
            subject = f"Your SnapFlow {batch_time.capitalize()} Update"
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
                notification=None,  # No specific notification for batches
                recipient_email=user.email,
                subject=subject,
                body=plain_message,
                status='sent'
            )
            
            # Mark all included notifications as sent
            notification_ids = [n.id for n in notifications]
            Notification.objects.filter(id__in=notification_ids).update(is_email_sent=True)
            
            # Remove the pending notifications
            pending_notifications.delete()
            
            logger.info(f"Sent batch email to user ID: {user_id} with {len(notifications)} notifications")
            return True
        except Exception as e:
            logger.error(f"Error sending batch email to user ID: {user_id}: {e}")
            traceback.print_exc()
            return False