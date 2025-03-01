# In your_app/management/commands/increase_upload_size.py

from django.core.management.base import BaseCommand
from events.models import EventConfiguration

class Command(BaseCommand):
    help = 'Increases max upload size for all event configurations'

    def handle(self, *args, **kwargs):
        count = EventConfiguration.objects.all().update(max_upload_size=52428800)  # 50MB
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} configurations'))