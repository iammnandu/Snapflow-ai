# notifications/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Notification, NotificationPreference
from .services import NotificationService
from .forms import NotificationPreferenceForm

@login_required
def notification_list(request):
    """Display a list of user's notifications"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    # Paginate results
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'notifications/list.html', {
        'page_obj': page_obj,
        'unread_count': unread_count,
    })

@login_required
def notification_detail(request, notification_id):
    """View a single notification and mark it as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    
    # Mark as read if it's not already
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
    
    # Redirect to the content object if available
    if notification.content_object:
        return HttpResponseRedirect(notification.get_absolute_url())
    
    # Otherwise, redirect back to the notification list
    messages.info(request, "Notification viewed")
    return redirect('notifications:list')

@login_required
def mark_all_as_read(request):
    """Mark all notifications as read"""
    if request.method == 'POST':
        NotificationService.mark_all_as_read(request.user)
        messages.success(request, "All notifications marked as read")
    
    return redirect('notifications:list')

@login_required
def mark_as_read(request, notification_id):
    """Mark a specific notification as read"""
    if request.method == 'POST':
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        messages.success(request, "Notification marked as read")
    
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