from .services import get_unread_count

def notification_count(request):
    """
    Add unread notification count to context for all templates.
    """
    count = 0
    if request.user.is_authenticated:
        count = get_unread_count(request.user)
    
    return {
        'unread_notification_count': count
    }