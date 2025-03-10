from events.models import Event
from .models import BestShot, DuplicateGroup

class HighlightsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_template_response(self, request, response):
        # Check if we're in an event context
        if hasattr(response, 'context_data') and 'event' in response.context_data:
            event = response.context_data['event']
            
            # Only process if event is an Event instance
            if isinstance(event, Event):
                # Add highlights data to the context
                response.context_data['has_highlights'] = BestShot.objects.filter(event=event).exists()
                response.context_data['has_duplicates'] = DuplicateGroup.objects.filter(event=event).exists()
                response.context_data['duplicate_count'] = DuplicateGroup.objects.filter(event=event).count()
                
        return response