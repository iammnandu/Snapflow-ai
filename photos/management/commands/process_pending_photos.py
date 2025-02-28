from django.core.management.base import BaseCommand
from photos.models import EventPhoto
from photos.tasks import process_photo

class Command(BaseCommand):
    help = 'Process all pending photos that have not been processed yet'

    def handle(self, *args, **options):
        pending_photos = EventPhoto.objects.filter(processed=False)
        count = pending_photos.count()
        
        self.stdout.write(f"Found {count} photos to process")
        
        for photo in pending_photos:
            self.stdout.write(f"Queuing photo {photo.id} for processing")
            process_photo.delay(photo.id)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully queued {count} photos for processing"))