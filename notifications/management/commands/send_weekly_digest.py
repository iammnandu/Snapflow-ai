# notifications/management/commands/send_weekly_digest.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from notifications.models import Notification, NotificationPreference, EmailLog
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send weekly notification digests to users who opted in'
    
    def handle(self, *args, **options):
        # Get last week's date range
        now = timezone.now()
        last_week = now - timedelta(days=7)
        
        # Find users who want weekly digests
        preferences = NotificationPreference.objects.filter(receive_weekly_digest=True)
        
        for pref in preferences:
            user = pref.user
            
            # Get last week's notifications for this user
            notifications = Notification.objects.filter(
                recipient=user,
                created_at__gte=last_week,
                created_at__lt=now
            )
            
            # Skip if no notifications
            if not notifications.exists():
                continue
            
            # Group by type
            notification_counts = notifications.values('notification_type').annotate(
                count=Count('id')
            )
            
            # Prepare context
            context = {
                'user': user,
                'notifications': notifications,
                'notification_counts': notification_counts,
                'notification_total': notifications.count(),
                'site_name': 'SnapFlow',
                'site_url': settings.SITE_URL,
                'week_start': last_week.strftime('%B %d'),
                'week_end': now.strftime('%B %d, %Y')
            }
            
            # Render email
            html_message = render_to_string('notifications/emails/weekly_digest.html', context)
            plain_message = strip_tags(html_message)
            subject = f"SnapFlow Weekly Digest: {notifications.count()} notifications this week"
            
            # Send email
            try:
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
                    recipient_email=user.email,
                    subject=subject,
                    body=plain_message,
                    status='sent'
                )
                
                self.stdout.write(self.style.SUCCESS(f"Sent weekly digest to {user.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send digest to {user.email}: {e}"))
                
                # Log error
                EmailLog.objects.create(
                    recipient_email=user.email,
                    subject=subject,
                    body=str(e),
                    status='error'
                )