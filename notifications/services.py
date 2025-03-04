from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse

from .models import Notification, NotificationPreference
from users.models import CustomUser
from events.models import Event
from photos.models import EventPhoto

def create_notification(recipient, notification_type, title, message, **kwargs):
    """
    Create a new notification for a user.
    
    Args:
        recipient: CustomUser object
        notification_type: Type of notification (from Notification.NOTIFICATION_TYPES)
        title: Notification title
        message: Notification message
        **kwargs: Additional data like event, photo, from_user, action_url, priority
    
    Returns:
        Created Notification object
    """
    # Create the notification
    notification = Notification(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        event=kwargs.get('event'),
        photo=kwargs.get('photo'),
        from_user=kwargs.get('from_user'),
        action_url=kwargs.get('action_url'),
        priority=kwargs.get('priority', 'medium')
    )
    notification.save()
    
    # Check if email should be sent based on user preferences
    should_email = _should_send_email(recipient, notification_type)
    
    if should_email:
        _send_email_notification(notification)
        notification.email_sent = True
        notification.save()
    
    return notification


def _should_send_email(user, notification_type):
    """Determine if an email should be sent based on user preferences."""
    try:
        prefs = NotificationPreference.objects.get(user=user)
        
        # Map notification type to preference field
        pref_map = {
            'photo_upload': prefs.email_photo_upload,
            'face_recognition': prefs.email_face_recognition,
            'comment': prefs.email_comments,
            'like': prefs.email_likes,
            'event_invitation': prefs.email_event_invitation,
            'crew_assignment': prefs.email_crew_assignment,
            'event_reminder': prefs.email_event_reminder,
            # System notifications are always sent
            'system': True,
            'access_request': True,
            'access_granted': True,
        }
        
        return pref_map.get(notification_type, False)
        
    except NotificationPreference.DoesNotExist:
        # Default to sending email if no preferences set
        return True


def _send_email_notification(notification):
    """Send an email for the notification."""
    context = {
        'notification': notification,
        'recipient': notification.recipient,
        'site_url': settings.SITE_URL,
    }
    
    html_message = render_to_string('notifications/email/notification.html', context)
    plain_message = render_to_string('notifications/email/notification_plain.txt', context)
    
    send_mail(
        subject=notification.title,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.recipient.email],
        html_message=html_message,
        fail_silently=True
    )


def mark_all_as_read(user):
    """Mark all notifications as read for a user."""
    Notification.objects.filter(recipient=user, read=False).update(
        read=True, 
        read_at=timezone.now()
    )


def get_unread_count(user):
    """Get count of unread notifications for a user."""
    return Notification.objects.filter(recipient=user, read=False).count()


# Specific notification creation functions for different events in the system

def notify_photo_upload(event, uploader, photo_count):
    """Notify event organizer when photos are uploaded."""
    organizer = event.organizer
    
    # Only notify if user has enabled this notification
    try:
        prefs = NotificationPreference.objects.get(user=organizer)
        if not prefs.notify_photo_upload:
            return None
    except NotificationPreference.DoesNotExist:
        pass  # Continue with default behavior
    
    title = f"New photos uploaded to {event.title}"
    message = f"{uploader.first_name} {uploader.last_name} uploaded {photo_count} new photos to your event."
    action_url = reverse('event_gallery', kwargs={'slug': event.slug})
    
    return create_notification(
        recipient=organizer,
        notification_type='photo_upload',
        title=title,
        message=message,
        event=event,
        from_user=uploader,
        action_url=action_url
    )


def notify_face_recognition(user, photo, event, confidence_score):
    """Notify a participant when they are recognized in a photo."""
    # Check if user wants to receive these notifications
    try:
        prefs = NotificationPreference.objects.get(user=user)
        if not prefs.notify_face_recognition:
            return None
    except NotificationPreference.DoesNotExist:
        pass
    
    title = f"You were recognized in a photo"
    message = f"You've been identified in a new photo from {event.title} with {confidence_score:.0%} confidence."
    action_url = reverse('photo_detail', kwargs={'pk': photo.id})
    
    return create_notification(
        recipient=user,
        notification_type='face_recognition',
        title=title,
        message=message,
        event=event,
        photo=photo,
        action_url=action_url
    )


def notify_comment(photo, commenter, commented_user):
    """Notify when someone comments on a photo."""
    if commenter == commented_user:
        return None  # Don't notify users about their own comments
    
    # Check user preferences
    try:
        prefs = NotificationPreference.objects.get(user=commented_user)
        if not prefs.notify_comments:
            return None
    except NotificationPreference.DoesNotExist:
        pass
    
    title = "New comment on your photo"
    message = f"{commenter.first_name} {commenter.last_name} commented on your photo."
    action_url = reverse('photo_detail', kwargs={'pk': photo.id})
    
    return create_notification(
        recipient=commented_user,
        notification_type='comment',
        title=title,
        message=message,
        photo=photo,
        from_user=commenter,
        action_url=action_url
    )


def notify_like(photo, liker, photo_owner):
    """Notify when someone likes a photo."""
    if liker == photo_owner:
        return None  # Don't notify users about their own likes
    
    # Check user preferences
    try:
        prefs = NotificationPreference.objects.get(user=photo_owner)
        if not prefs.notify_likes:
            return None
    except NotificationPreference.DoesNotExist:
        pass
    
    title = "Someone liked your photo"
    message = f"{liker.first_name} {liker.last_name} liked your photo."
    action_url = reverse('photo_detail', kwargs={'pk': photo.id})
    
    return create_notification(
        recipient=photo_owner,
        notification_type='like',
        title=title,
        message=message,
        photo=photo,
        from_user=liker,
        action_url=action_url
    )


def notify_event_invitation(event, invitee, inviter, role='participant'):
    """Notify when a user is invited to an event."""
    title = f"You've been invited to {event.title}"
    
    if role == 'crew':
        message = f"{inviter.first_name} {inviter.last_name} has invited you to join the photography crew for {event.title}."
        action_url = reverse('crew_invitation_response', kwargs={'event_slug': event.slug})
        notification_type = 'crew_assignment'
    else:
        message = f"{inviter.first_name} {inviter.last_name} has invited you to join {event.title} as a participant."
        action_url = reverse('event_invitation_response', kwargs={'event_slug': event.slug})
        notification_type = 'event_invitation'
    
    return create_notification(
        recipient=invitee,
        notification_type=notification_type,
        title=title,
        message=message,
        event=event,
        from_user=inviter,
        action_url=action_url,
        priority='high'
    )


def notify_event_reminder(event, participant, days_until_event):
    """Send event reminder notification."""
    title = f"Reminder: {event.title} is in {days_until_event} days"
    message = f"This is a reminder that {event.title} will be starting in {days_until_event} days at {event.location}."
    action_url = reverse('event_detail', kwargs={'slug': event.slug})
    
    return create_notification(
        recipient=participant,
        notification_type='event_reminder',
        title=title,
        message=message,
        event=event,
        action_url=action_url
    )


def notify_processing_complete(photographer, event, photo_count):
    """Notify photographer when their uploaded photos have been processed."""
    title = "Photo processing complete"
    message = f"All {photo_count} photos you uploaded for {event.title} have been processed and are now available."
    action_url = reverse('event_gallery', kwargs={'slug': event.slug})
    
    return create_notification(
        recipient=photographer,
        notification_type='processing_complete',
        title=title,
        message=message,
        event=event,
        action_url=action_url
    )


def notify_access_request(organizer, requester, event):
    """Notify organizer of a new access request."""
    title = "New event access request"
    message = f"{requester.first_name} {requester.last_name} has requested access to your event {event.title}."
    action_url = reverse('event_access_requests', kwargs={'slug': event.slug})
    
    return create_notification(
        recipient=organizer,
        notification_type='access_request',
        title=title,
        message=message,
        event=event,
        from_user=requester,
        action_url=action_url,
        priority='high'
    )


def notify_access_granted(user, event, granted_by):
    """Notify user when their access request is granted."""
    title = "Event access granted"
    message = f"Your request to access {event.title} has been approved."
    action_url = reverse('event_detail', kwargs={'slug': event.slug})
    
    return create_notification(
        recipient=user,
        notification_type='access_granted',
        title=title,
        message=message,
        event=event,
        from_user=granted_by,
        action_url=action_url
    )