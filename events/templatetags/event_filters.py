# events/templatetags/event_filters.py
from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given separator"""
    return value.split(arg)

@register.filter
def filesizeformat(bytes):
    """Format a size in bytes to human-readable format"""
    try:
        bytes = float(bytes)
        kb = bytes / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        mb = kb / 1024
        if mb < 1024:
            return f"{mb:.1f} MB"
        gb = mb / 1024
        return f"{gb:.1f} GB"
    except:
        return '0 KB'