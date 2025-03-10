import time
from django.core.management.base import BaseCommand
from django.db.models import Q
from photos.models import EventPhoto
from highlights.tasks import analyze_photo_quality, find_duplicate_photos

class Command(BaseCommand):
    help = 'Process all existing photos to find best shots and duplicates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event',
            type=int,
            help='Process photos only for specific event ID',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of photos to process in each batch',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between batches in seconds',
        )

    def handle(self, *args, **options):
        event_id = options.get('event')
        batch_size = options.get('batch_size')
        delay = options.get('delay')
        
        # Get photos to process
        photos_query = EventPhoto.objects.all()
        
        if event_id:
            photos_query = photos_query.filter(event_id=event_id)
            self.stdout.write(f"Processing only photos from event ID: {event_id}")
        
        # Count the photos
        total_photos = photos_query.count()
        self.stdout.write(f"Found {total_photos} photos to process")
        
        # Process photos in batches
        processed = 0
        batches = 0
        
        # First, analyze all photos for quality
        photo_ids = list(photos_query.values_list('id', flat=True))
        
        for i in range(0, len(photo_ids), batch_size):
            batch = photo_ids[i:i+batch_size]
            batches += 1
            
            self.stdout.write(f"Processing batch {batches} ({len(batch)} photos)...")
            
            # Submit quality analysis tasks
            for photo_id in batch:
                analyze_photo_quality.delay(photo_id)
                processed += 1
            
            self.stdout.write(f"Progress: {processed}/{total_photos} photos ({(processed/total_photos)*100:.1f}%)")
            
            # Delay between batches to prevent overloading the worker
            if delay > 0 and i + batch_size < len(photo_ids):
                time.sleep(delay)
        
        # Second, find duplicates for each event
        if event_id:
            # Process duplicates for specified event
            self.stdout.write(f"Finding duplicates for event ID: {event_id}")
            find_duplicate_photos.delay(event_id)
        else:
            # Process duplicates for all events
            events = set(photos_query.values_list('event_id', flat=True))
            self.stdout.write(f"Finding duplicates for {len(events)} events")
            
            for event_id in events:
                self.stdout.write(f"Finding duplicates for event ID: {event_id}")
                find_duplicate_photos.delay(event_id)
                time.sleep(delay)  # Small delay between events
        
        self.stdout.write(self.style.SUCCESS(f"Successfully queued processing for {processed} photos"))