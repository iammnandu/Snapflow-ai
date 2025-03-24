# privacy/templatetags/privacy_tags.py
from django import template
from privacy.tasks import check_photo_privacy

register = template.Library()

@register.simple_tag
def get_photo_privacy_status(photo, user=None):
    """Return privacy status information for a photo."""
    return check_photo_privacy(photo, user)