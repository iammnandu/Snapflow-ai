# notifications/tasks.py
from celery import shared_task
from .services import NotificationService

@shared_task
def send_notification_email(notification_id):
    """Background task to send notification email"""
    from .models import Notification
    try:
        notification = Notification.objects.get(id=notification_id)
        NotificationService._send_email_notification(notification)
        return f"Email sent for notification {notification_id}"
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error sending email for notification {notification_id}: {str(e)}"

@shared_task
def process_morning_email_batch():
    """Process morning batch of emails"""
    NotificationService.process_email_batches('morning')
    return "Morning email batch processed"

@shared_task
def process_evening_email_batch():
    """Process evening batch of emails"""
    NotificationService.process_email_batches('evening')
    return "Evening email batch processed"

@shared_task
def send_daily_digest():
    """Send daily digest emails to users who have opted in"""
    from .models import NotificationPreference, Notification
    from django.utils import timezone
    from datetime import timedelta
    
    # Get users who want daily digests
    users_with_daily_digest = NotificationPreference.objects.filter(
        receive_daily_digest=True
    ).values_list('user', flat=True)
    
    # Get notifications from the last 24 hours
    yesterday = timezone.now() - timedelta(days=1)
    
    for user_id in users_with_daily_digest:
        notifications = Notification.objects.filter(
            recipient_id=user_id,
            created_at__gte=yesterday
        )
        
        if notifications.exists():
            # Send digest email
            NotificationService._send_digest_email(user_id, notifications, 'daily')
    
    return f"Daily digest sent to {len(users_with_daily_digest)} users"

@shared_task
def send_weekly_digest():
    """Send weekly digest emails to users who have opted in"""
    from .models import NotificationPreference, Notification
    from django.utils import timezone
    from datetime import timedelta
    
    # Get users who want weekly digests
    users_with_weekly_digest = NotificationPreference.objects.filter(
        receive_weekly_digest=True
    ).values_list('user', flat=True)
    
    # Get notifications from the last 7 days
    last_week = timezone.now() - timedelta(days=7)
    
    for user_id in users_with_weekly_digest:
        notifications = Notification.objects.filter(
            recipient_id=user_id,
            created_at__gte=last_week
        )
        
        if notifications.exists():
            # Send digest email
            NotificationService._send_digest_email(user_id, notifications, 'weekly')
    
    return f"Weekly digest sent to {len(users_with_weekly_digest)} users"