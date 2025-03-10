# Add this in your app/templatetags/notification_filters.py

from django import template

register = template.Library()

@register.filter
def get_by_index(list_obj, index):
    """Return item from list by index"""
    try:
        return list_obj[index]
    except (IndexError, TypeError):
        return None