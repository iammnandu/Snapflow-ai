import io
import numpy as np
from celery import shared_task
from PIL import Image, ImageChops, ImageStat
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from events.models import Event
from photos.models import EventPhoto
from .models import BestShot, DuplicateGroup, DuplicatePhoto

# ----- Best Shots Tasks -----

@shared_task
def analyze_photo_quality(photo_id):
    """Analyze a single photo for quality metrics using advanced analysis."""
    try:
        photo = EventPhoto.objects.get(id=photo_id)
        
        # Skip if already processed and has quality score
        if photo.highlights and photo.quality_score is not None:
            return
        
        # Import here to avoid circular imports
        from .analysis import analyze_photo_advanced
        
        # Perform advanced analysis
        results = analyze_photo_advanced(photo)
        
        # Save the quality score to the photo
        photo.quality_score = results['quality_score']
        photo.highlights = True
        photo.save(update_fields=['quality_score', 'highlights'])
        
        # Create or update best shots by category
        event = photo.event
        
        # Add to OVERALL category if it's a good quality photo
        if results['quality_score'] > 75:
            # Check if we already have enough best shots
            existing_count = BestShot.objects.filter(event=event, category='OVERALL').count()
            
            if existing_count < 10:
                # Always add if we have fewer than 10
                BestShot.objects.create(
                    event=event,
                    photo=photo,
                    score=results['quality_score'],
                    category='OVERALL'
                )
            else:
                # Otherwise, replace the lowest-scoring shot if this one is better
                lowest_shot = BestShot.objects.filter(event=event, category='OVERALL').order_by('score').first()
                if lowest_shot and results['quality_score'] > lowest_shot.score:
                    lowest_shot.photo = photo
                    lowest_shot.score = results['quality_score']
                    lowest_shot.save()
        
        # Add to specific categories based on analysis
        for category in results['categories']:
            if category in ['PORTRAIT', 'GROUP', 'ACTION', 'COMPOSITION', 'LIGHTING']:
                # Check if we already have enough shots in this category
                existing_count = BestShot.objects.filter(event=event, category=category).count()
                category_score = results['quality_score']
                
                # Adjust category-specific score
                if category == 'COMPOSITION':
                    category_score = results['composition_score']
                elif category == 'LIGHTING':
                    category_score = results['lighting_score']
                
                if existing_count < 5:
                    # Always add if we have fewer than 5
                    BestShot.objects.create(
                        event=event,
                        photo=photo,
                        score=category_score,
                        category=category
                    )
                else:
                    # Otherwise, replace the lowest-scoring shot if this one is better
                    lowest_shot = BestShot.objects.filter(event=event, category=category).order_by('score').first()
                    if lowest_shot and category_score > lowest_shot.score:
                        lowest_shot.photo = photo
                        lowest_shot.score = category_score
                        lowest_shot.save()
        
        # Check for duplicates after processing
        find_duplicate_photos.delay(photo.event.id)
        
        return results['quality_score']
        
    except Exception as e:
        print(f"Error analyzing photo {photo_id}: {str(e)}")
        return None


@shared_task
def update_event_best_shots(event_id):
    """Update the best shots for an event."""
    try:
        event = Event.objects.get(id=event_id)
        photos = EventPhoto.objects.filter(event=event, highlights=True).exclude(quality_score=None)
        
        if not photos.exists():
            return
        
        with transaction.atomic():
            # Get best overall quality photos (top 5)
            best_overall = photos.order_by('-quality_score')[:5]
            
            # Clear existing best shots for this event and category
            BestShot.objects.filter(event=event, category='OVERALL').delete()
            
            # Create new best shot entries
            for photo in best_overall:
                BestShot.objects.create(
                    event=event,
                    photo=photo,
                    score=photo.quality_score,
                    category='OVERALL'
                )
            
            # TODO: Add more advanced category detection (portrait, group, etc.)
            # This would use the face detection data you already have
            
    except Exception as e:
        print(f"Error updating best shots for event {event_id}: {str(e)}")


# ----- Duplicate Detection Tasks -----
@shared_task
def find_duplicate_photos(event_id):
    """Find duplicate photos for an event."""
    try:
        event = Event.objects.get(id=event_id)
        photos = EventPhoto.objects.filter(event=event)
        
        if photos.count() < 2:
            return
        
        # Dictionary to store photo signatures/hashes for comparison
        photo_signatures = {}
        
        # Calculate signatures for all photos
        for photo in photos:
            try:
                # Calculate a perceptual hash of the image for comparison
                img = Image.open(photo.image.path).resize((16, 16), Image.Resampling.LANCZOS).convert('L')
                # Convert to a simple hash array
                pixels = np.array(img).flatten()
                # Normalize
                pixels = (pixels > np.mean(pixels)).astype(int)
                photo_signatures[photo.id] = pixels
            except Exception as e:
                print(f"Error processing photo {photo.id}: {str(e)}")
        
        # Clear existing duplicate groups for this event to prevent duplicates
        with transaction.atomic():
            # Get all duplicate groups for this event
            old_groups = DuplicateGroup.objects.filter(event=event)
            # Delete them
            if old_groups.exists():
                old_groups.delete()
        
        # Find groups of similar photos
        similarity_threshold = 0.85  # 85% similarity
        processed = set()
        duplicate_groups = []
        
        for photo_id, signature in photo_signatures.items():
            if photo_id in processed:
                continue
                
            # Start a new group with this photo
            current_group = [(photo_id, 1.0)]  # Add original photo with perfect similarity
            processed.add(photo_id)
            
            # Compare with all other unprocessed photos
            for other_id, other_signature in photo_signatures.items():
                if photo_id == other_id or other_id in processed:
                    continue
                    
                # Calculate similarity (Hamming similarity)
                similarity = 1.0 - np.mean(np.abs(signature - other_signature))
                
                if similarity >= similarity_threshold:
                    current_group.append((other_id, similarity))
                    processed.add(other_id)
            
            # If we found similar photos (group has more than just the original photo)
            if len(current_group) > 1:
                # Sort by similarity (highest first)
                current_group.sort(key=lambda x: x[1], reverse=True)
                duplicate_groups.append(current_group)
        
        # Save the duplicate groups to the database
        with transaction.atomic():
            for group_photos in duplicate_groups:
                # Create a new duplicate group
                dup_group = DuplicateGroup.objects.create(
                    event=event,
                    similarity_threshold=similarity_threshold
                )
                
                # Add photos to the group
                for i, (photo_id, similarity) in enumerate(group_photos):
                    DuplicatePhoto.objects.create(
                        group=dup_group,
                        photo=EventPhoto.objects.get(id=photo_id),
                        is_primary=(i == 0),  # First photo is primary
                        similarity_score=similarity
                    )
        
        return len(duplicate_groups)
        
    except Exception as e:
        print(f"Error finding duplicates for event {event_id}: {str(e)}")
        return None


# ----- Signal Handlers -----

@shared_task
def process_new_photo(photo_id):
    """Process a newly uploaded or modified photo."""
    # First analyze quality
    analyze_photo_quality(photo_id)
    
    # Then check for duplicates
    photo = EventPhoto.objects.get(id=photo_id)
    find_duplicate_photos(photo.event.id)




# Add this to tasks.py

import logging
from django.db import transaction
from functools import lru_cache

logger = logging.getLogger(__name__)

# Using LRU cache to avoid re-computing signatures for photos
@lru_cache(maxsize=128)
def calculate_photo_signature(photo_path):
    """Calculate a perceptual hash for an image."""
    try:
        img = Image.open(photo_path).resize((16, 16), Image.Resampling.LANCZOS).convert('L')
        pixels = np.array(img).flatten()
        # Normalize
        return (pixels > np.mean(pixels)).astype(int)
    except Exception as e:
        logger.error(f"Error calculating signature for {photo_path}: {str(e)}")
        return None

@shared_task
def process_photos_in_batches(event_id, batch_size=50):
    """Process photos in batches for large events."""
    try:
        event = Event.objects.get(id=event_id)
        all_photos = EventPhoto.objects.filter(event=event).order_by('id')
        total_photos = all_photos.count()
        
        if total_photos == 0:
            return
        
        # Process in batches
        for offset in range(0, total_photos, batch_size):
            batch = all_photos[offset:offset+batch_size]
            for photo in batch:
                analyze_photo_quality.delay(photo.id)
                
        # After all batches are processed, find duplicates
        find_duplicate_photos.delay(event_id)
            
    except Exception as e:
        logger.error(f"Error processing photos in batches for event {event_id}: {str(e)}")