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
                best_shots = BestShot.objects.filter(event=event)
                response.context_data['has_highlights'] = best_shots.exists()
                response.context_data['has_duplicates'] = DuplicateGroup.objects.filter(event=event).exists()
                response.context_data['duplicate_count'] = DuplicateGroup.objects.filter(event=event).count()
                
                # Add problem photo counts
                response.context_data['blurry_count'] = best_shots.filter(category='BLURRY').count()
                response.context_data['underexposed_count'] = best_shots.filter(category='UNDEREXPOSED').count()
                response.context_data['overexposed_count'] = best_shots.filter(category='OVEREXPOSED').count()
                response.context_data['accidental_count'] = best_shots.filter(category='ACCIDENTAL').count()
                
        return response