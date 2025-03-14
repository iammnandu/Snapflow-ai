# notifications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import Notification, NotificationPreference
from .services import NotificationService
from .forms import NotificationPreferenceForm

@login_required
def notification_list(request):
    """Display a list of user's notifications"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Filter by type if specified
    notification_type = request.GET.get('type')
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    # Filter by read status if specified
    read_status = request.GET.get('status')
    if read_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Paginate results
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()
    
    # Get available notification types for filtering
    notification_types = Notification.NOTIFICATION_TYPES
    
    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
        'notification_types': notification_types,
        'current_type': notification_type,
        'current_status': read_status,
    })

@login_required
def notification_detail(request, notification_id):
    """View a single notification and mark it as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    # Mark as read if it's not already
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    
    # Check if the notification has a target URL to redirect to
    redirect_url = request.GET.get('redirect')
    if redirect_url == 'target':
        # Check if content object exists
        if hasattr(notification, 'content_object') and notification.content_object is not None:
            target_url = notification.get_absolute_url()
            # Only redirect if the target URL isn't the notifications list
            if target_url != reverse('notifications:list'):
                return HttpResponseRedirect(target_url)
            else:
                # Add a message to inform the user
                messages.info(request, "The content this notification refers to is no longer available.")
        else:
            # Add a message to inform the user
            messages.info(request, "The content this notification refers to is no longer available.")
    
    # Check if content object exists for the template
    content_exists = hasattr(notification, 'content_object') and notification.content_object is not None
    
    return render(request, 'notifications/notification_detail.html', {
        'notification': notification,
        'content_exists': content_exists
    })


@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications as read"""
    count = NotificationService.mark_all_as_read(request.user)
    messages.success(request, f"{count} notifications marked as read")
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'count': count})
    
    return redirect('notifications:list')

@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Mark a specific notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    messages.success(request, "Notification marked as read")
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:list')

@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    messages.success(request, "Notification deleted")
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:list')

@login_required
def preferences(request):
    """View and update notification preferences"""
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated successfully")
            return redirect('notifications:preferences')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    return render(request, 'notifications/preferences.html', {
        'form': form,
        'preferences': preferences,
    })


@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a specific notification"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    messages.success(request, "Notification deleted")
    
    # Support AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notifications:list')