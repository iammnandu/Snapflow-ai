from django.apps import AppConfig

class HighlightsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'highlights'
    
    def ready(self):
        import highlights.signals
        highlights.signals.ready()