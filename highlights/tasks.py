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

import logging
logger = logging.getLogger(__name__)


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
        
        # Define consistent thresholds for each category
        thresholds = {
            'OVERALL': {'limit': 10, 'min_score': 70},
            'PORTRAIT': {'limit': 5, 'min_score': 75},
            'GROUP': {'limit': 5, 'min_score': 75},
            'ACTION': {'limit': 5, 'min_score': 75},
            'COMPOSITION': {'limit': 5, 'min_score': 80},
            'LIGHTING': {'limit': 5, 'min_score': 80},
            # Add problem categories with lower thresholds so they get tracked
            'BLURRY': {'limit': 3, 'min_score': 20},
            'UNDEREXPOSED': {'limit': 3, 'min_score': 20},
            'OVEREXPOSED': {'limit': 3, 'min_score': 20},
            'ACCIDENTAL': {'limit': 3, 'min_score': 10},
        }
        
        # Add to OVERALL category if it's a good quality photo
        if results['quality_score'] > thresholds['OVERALL']['min_score']:
            update_category_best_shot(event, photo, results['quality_score'], 'OVERALL', 
                                      thresholds['OVERALL']['limit'])
        
        # Add to specific categories based on analysis results
        for category in results['categories']:
            if category in thresholds:
                # Get category-specific score
                if category == 'COMPOSITION':
                    category_score = results['composition_score']
                elif category == 'LIGHTING':
                    category_score = results['lighting_score']
                elif category == 'BLURRY':
                    category_score = results['blur_score']
                elif category in ['UNDEREXPOSED', 'OVEREXPOSED']:
                    category_score = results['exposure_score']
                else:
                    category_score = results['quality_score']
                    
                # Only add if the score meets the minimum threshold
                if category_score > thresholds[category]['min_score']:
                    update_category_best_shot(event, photo, category_score, category, 
                                             thresholds[category]['limit'])
        
        # Check for duplicates after processing
        find_duplicate_photos.delay(photo.event.id)
        
        return results['quality_score']
        
    except Exception as e:
        logger.error(f"Error analyzing photo {photo_id}: {str(e)}")
        return None


def update_category_best_shot(event, photo, score, category, limit):
    """Helper function to update best shots for a category."""
    try:
        with transaction.atomic():
            existing_count = BestShot.objects.filter(event=event, category=category).count()
            
            if existing_count < limit:
                # Always add if we have fewer than the limit
                BestShot.objects.create(
                    event=event,
                    photo=photo,
                    score=score,
                    category=category
                )
            else:
                # Otherwise, replace the lowest-scoring shot if this one is better
                lowest_shot = BestShot.objects.filter(
                    event=event, category=category
                ).order_by('score').first()
                
                if lowest_shot and score > lowest_shot.score:
                    lowest_shot.photo = photo
                    lowest_shot.score = score
                    lowest_shot.save()
    except Exception as e:
        logger.error(f"Error updating best shot for category {category}: {str(e)}")


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
            
    except Exception as e:
        logger.error(f"Error updating best shots for event {event_id}: {str(e)}")


# ----- Duplicate Detection Tasks -----
@shared_task
def find_duplicate_photos(event_id):
    """Find duplicate photos for an event using improved detection."""
    try:
        event = Event.objects.get(id=event_id)
        photos = EventPhoto.objects.filter(event=event)
        
        if photos.count() < 2:
            return
        
        # Dictionary to store multiple signatures for better comparison
        photo_signatures = {}
        
        # Calculate signatures for all photos
        for photo in photos:
            try:
                # Calculate both perceptual hash and color histogram for better comparison
                img = Image.open(photo.image.path)
                
                # 1. Perceptual hash (sensitive to structure)
                img_small = img.resize((16, 16), Image.Resampling.LANCZOS).convert('L')
                pixels = np.array(img_small).flatten()
                phash = (pixels > np.mean(pixels)).astype(int)
                
                # 2. Color histogram (sensitive to color distribution)
                img_rgb = img.resize((64, 64), Image.Resampling.LANCZOS).convert('RGB')
                r, g, b = img_rgb.split()
                hist_r = np.array(r.histogram()) / 256.0
                hist_g = np.array(g.histogram()) / 256.0
                hist_b = np.array(b.histogram()) / 256.0
                
                # Store both signatures
                photo_signatures[photo.id] = {
                    'phash': phash,
                    'color_hist': np.concatenate([hist_r, hist_g, hist_b]),
                    'quality_score': photo.quality_score or 0,
                    'file_size': photo.image.size,
                    'resolution': img.size[0] * img.size[1],
                    'photo_obj': photo  # Store the photo object for convenience
                }
            except Exception as e:
                logger.error(f"Error processing photo {photo.id}: {str(e)}")
        
        # Clear existing duplicate groups
        with transaction.atomic():
            old_groups = DuplicateGroup.objects.filter(event=event)
            if old_groups.exists():
                old_groups.delete()
        
        # Find groups with improved detection
        processed = set()
        duplicate_groups = []
        
        # Set more strict thresholds to avoid false positives
        phash_threshold = 0.92  # Increased from 0.85 to 0.92 (92% similarity required)
        color_threshold = 0.88  # Increased from 0.80 to 0.88 (88% similarity required)
        
        # Function to calculate structural similarity using hamming distance
        def calculate_phash_similarity(hash1, hash2):
            # Use hamming distance (count of differing bits)
            hamming_distance = np.sum(hash1 != hash2)
            # Convert to similarity score (0-1)
            max_distance = len(hash1)
            similarity = 1.0 - (hamming_distance / max_distance)
            return similarity
        
        # Function to calculate color histogram similarity
        def calculate_color_similarity(hist1, hist2):
            # Use histogram intersection metric
            intersection = np.sum(np.minimum(hist1, hist2))
            return intersection
        
        for photo_id, signatures in photo_signatures.items():
            if photo_id in processed:
                continue
                
            # Start a new group with this photo
            current_group = [(photo_id, 1.0, signatures)]  # Add original with perfect similarity
            processed.add(photo_id)
            
            # Compare with all other unprocessed photos
            for other_id, other_signatures in photo_signatures.items():
                if photo_id == other_id or other_id in processed:
                    continue
                    
                # Calculate structural similarity (perceptual hash)
                phash_sim = calculate_phash_similarity(signatures['phash'], other_signatures['phash'])
                
                # Calculate color similarity (using histogram intersection)
                color_sim = calculate_color_similarity(signatures['color_hist'], other_signatures['color_hist'])
                
                # Calculate time difference if available
                time_factor = 1.0  # Default - no time adjustment
                if hasattr(signatures['photo_obj'], 'taken_at') and hasattr(other_signatures['photo_obj'], 'taken_at'):
                    if signatures['photo_obj'].taken_at and other_signatures['photo_obj'].taken_at:
                        # Photos taken far apart in time are less likely to be duplicates
                        time_diff = abs((signatures['photo_obj'].taken_at - other_signatures['photo_obj'].taken_at).total_seconds())
                        if time_diff > 300:  # More than 5 minutes apart
                            time_factor = 0.7  # Reduce similarity score
                
                # Combined similarity score (weighted average)
                combined_sim = (phash_sim * 0.6) + (color_sim * 0.4)
                combined_sim *= time_factor  # Apply time factor adjustment
                
                # Photos must meet BOTH thresholds to be considered duplicates
                if phash_sim >= phash_threshold and color_sim >= color_threshold:
                    current_group.append((other_id, combined_sim, other_signatures))
                    processed.add(other_id)
            
            # Only create a group if we found actual duplicates
            if len(current_group) > 1:
                # Sort by combined quality metrics (similarity, quality score, resolution)
                current_group.sort(key=lambda x: (
                    x[1],  # Similarity
                    x[2]['quality_score'],  # Quality score
                    x[2]['resolution']  # Resolution
                ), reverse=True)
                
                duplicate_groups.append(current_group)
        
        # Save the duplicate groups
        with transaction.atomic():
            for group_photos in duplicate_groups:
                dup_group = DuplicateGroup.objects.create(
                    event=event,
                    similarity_threshold=phash_threshold
                )
                
                # Add photos to the group
                for i, (photo_id, similarity, signatures) in enumerate(group_photos):
                    DuplicatePhoto.objects.create(
                        group=dup_group,
                        photo=signatures['photo_obj'],
                        is_primary=(i == 0),  # First photo is primary
                        similarity_score=similarity
                    )
        
        return len(duplicate_groups)
        
    except Exception as e:
        logger.error(f"Error finding duplicates for event {event_id}: {str(e)}")
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


@shared_task
def process_event_photos(event_id):
    """Process all photos for an event, using batches for large events."""
    try:
        event = Event.objects.get(id=event_id)
        photo_count = EventPhoto.objects.filter(event=event).count()
        
        # Use batch processing for large events
        if photo_count > 100:
            process_photos_in_batches.delay(event_id)
        else:
            # Process directly for smaller events
            photos = EventPhoto.objects.filter(event=event)
            for photo in photos:
                analyze_photo_quality.delay(photo.id)
            
            # Find duplicates after all photos are processed
            find_duplicate_photos.delay(event_id)
            
    except Exception as e:
        logger.error(f"Error initiating photo processing for event {event_id}: {str(e)}")