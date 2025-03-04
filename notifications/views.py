from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages

from .models import Notification, NotificationPreference
from .services import mark_all_as_read, get_unread_count
from .forms import NotificationPreferenceForm


@login_required
def notification_list(request):
    """Display a list of user notifications."""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Filter options
    filter_type = request.GET.get('type')
    if filter_type:
        notifications = notifications.filter(notification_type=filter_type)
    
    # Show only unread
    unread_only = request.GET.get('unread') == 'true'
    if unread_only:
        notifications = notifications.filter(read=False)
    
    # Pagination
    paginator = Paginator(notifications, 20)  # 20 notifications per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get notification types for filter dropdown
    notification_types = Notification.NOTIFICATION_TYPES
    
    context = {
        'page_obj': page_obj,
        'notification_types': notification_types,
        'filter_type': filter_type,
        'unread_only': unread_only,
        'unread_count': get_unread_count(request.user),
    }
    
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_detail(request, notification_id):
    """View a single notification and mark it as read."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    # Mark as read if not already
    if not notification.read:
        notification.mark_as_read()
    
    # Redirect to the action URL if it exists
    if notification.action_url:
        return HttpResponseRedirect(notification.action_url)
    
    # Otherwise, render the notification detail page
    return render(request, 'notifications/notification_detail.html', {'notification': notification})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'unread_count': get_unread_count(request.user)})
    
    return redirect('notification_list')


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all of a user's notifications as read."""
    mark_all_as_read(request.user)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'unread_count': 0})
    
    messages.success(request, "All notifications marked as read.")
    return redirect('notification_list')


@login_required
@require_POST
def delete_notification(request, notification_id):
    """Delete a specific notification."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'unread_count': get_unread_count(request.user)})
    
    messages.success(request, "Notification deleted.")
    return redirect('notification_list')


@login_required
def notification_preferences(request):
    """View and update notification preferences."""
    # Get or create preference object
    preferences, created = NotificationPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = NotificationPreferenceForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Notification preferences updated successfully.")
            return redirect('notification_preferences')
    else:
        form = NotificationPreferenceForm(instance=preferences)
    
    context = {
        'form': form,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'notifications/preferences.html', context)


@login_required
def unread_notification_count(request):
    """AJAX endpoint to get the current unread notification count."""
    count = get_unread_count(request.user)
    return JsonResponse({'count': count})