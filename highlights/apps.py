from django.apps import AppConfig

class HighlightsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'highlights'

    def ready(self):
        # Import signals here to avoid circular imports
        import highlights.signals