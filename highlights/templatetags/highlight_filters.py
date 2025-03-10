from django import template

register = template.Library()

@register.filter
def map_attribute(queryset, attribute):
    """Gets a specific attribute from all objects in a queryset"""
    return [getattr(item, attribute) for item in queryset]