# notifications/context_processors.py
def notification_processor(request):
    """Add notification data to context for all templates"""
    context = {
        'unread_notifications_count': 0,
        'recent_notifications': []
    }
    
    if request.user.is_authenticated:
        from .models import Notification
        
        # Get unread count
        context['unread_notifications_count'] = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        # Get 5 most recent notifications
        context['recent_notifications'] = Notification.objects.filter(
            recipient=request.user
        ).order_by('-created_at')[:5]
    
    return context