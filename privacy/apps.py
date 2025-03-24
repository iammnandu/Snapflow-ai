# privacy/apps.py
from django.apps import AppConfig

class PrivacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'privacy'
    
    def ready(self):
        import privacy.signals

