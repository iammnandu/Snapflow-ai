# photos/management/commands/process_photos.py
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from pathlib import Path
from deepface import DeepFace
from PIL import Image
import shutil
import cv2
from datetime import datetime
import tempfile
from photos.models import EventPhoto, UserPhotoMatch
from events.models import Event
from django.db.models import Q

User = get_user_model()

class Command(BaseCommand):
    help = 'Process photos in batch and match faces to users'

    def add_arguments(self, parser):
        parser.add_argument('--event', type=str, help='Event slug to process photos for')
        parser.add_argument('--user', type=str, help='Username to match photos for')
        parser.add_argument('--source', type=str, help='Source folder containing photos to import')
        parser.add_argument('--threshold', type=float, default=0.8, help='Confidence threshold (0-1)')

    def handle(self, *args, **options):
        event_slug = options.get('event')
        username = options.get('user')
        source_folder = options.get('source')
        threshold = options.get('threshold', 0.8)
        
        if not event_slug:
            self.stdout.write(self.style.ERROR('Please provide an event slug with --event'))
            return
            
        try:
            event = Event.objects.get(slug=event_slug)
        except Event.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Event with slug {event_slug} not found'))
            return
            
        if username:
            try:
                user = User.objects.get(username=username)
                self.stdout.write(self.style.SUCCESS(f'Processing photos for user: {user.get_full_name() or user.username}'))
                
                if not hasattr(user, 'profile_picture') or not user.profile_picture:
                    self.stdout.write(self.style.ERROR(f'User {username} does not have a profile picture'))
                    return
                    
                reference_image = os.path.join(settings.MEDIA_ROOT, str(user.profile_picture))
                
                if source_folder:
                    # Process external photos using PhotoOrganizer
                    self.process_external_photos(user, event, reference_image, source_folder, threshold)
                else:
                    # Process existing event photos for this user
                    self.process_event_photos(user, event, reference_image, threshold)
                    
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with username {username} not found'))
                return
        else:
            # Process all users for this event
            self.stdout.write(self.style.SUCCESS(f'Processing photos for all users in event: {event.title}'))
            self.process_all_users(event, threshold, source_folder)
            
    def process_external_photos(self, user, event, reference_image, source_folder, threshold):
        """Process photos from external folder and import matching ones to the event"""
        self.stdout.write(f"Processing external photos from {source_folder}")
        
        if not os.path.exists(source_folder):
            self.stdout.write(self.style.ERROR(f"Source folder {source_folder} does not exist"))
            return
            
        processed_count = 0
        matched_count = 0
        
        # Get list of supported image extensions
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        # Process each image in source folder
        for root, _, files in os.walk(source_folder):
            for filename in files:
                if Path(filename).suffix.lower() in supported_formats:
                    image_path = os.path.join(root, filename)
                    
                    try:
                        # Verify face match
                        result = DeepFace.verify(
                            img1_path=reference_image,
                            img2_path=image_path,
                            model_name='VGG-Face',
                            detector_backend='retinaface'
                        )
                        
                        processed_count += 1
                        
                        # If face matches with high confidence
                        if result['verified'] and result.get('distance', 1) < (1 - threshold):
                            matched_count += 1
                            
                            # Import photo to event
                            with open(image_path, 'rb') as f:
                                # Create a photo model
                                photo = EventPhoto(
                                    event=event,
                                    uploaded_by=user,
                                    caption=f"Imported photo featuring {user.get_full_name() or user.username}"
                                )
                                photo.image.save(filename, f)
                                photo.save()
                                
                                # Create face match
                                UserPhotoMatch.objects.create(
                                    photo=photo,
                                    user=user,
                                    confidence_score=round((1 - result.get('distance', 0)) * 100, 2)
                                )
                                
                                self.stdout.write(self.style.SUCCESS(f"Imported: {filename}"))
                                
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error processing {filename}: {str(e)}"))
                        continue
                        
                    # Print progress every 10 photos
                    if processed_count % 10 == 0:
                        self.stdout.write(f"Processed {processed_count} photos, found {matched_count} matches...")
                        
        self.stdout.write(self.style.SUCCESS(f"\nComplete! Processed {processed_count} photos"))
        self.stdout.write(self.style.SUCCESS(f"Found and imported {matched_count} photos matching {user.get_full_name() or user.username}"))
        
    def process_event_photos(self, user, event, reference_image, threshold):
        """Process existing event photos to find matches for this user"""
        self.stdout.write(f"Processing existing photos in event: {event.title}")
        
        photos = EventPhoto.objects.filter(event=event)
        processed_count = 0
        matched_count = 0
        
        for photo in photos:
            try:
                image_path = photo.image.path
                
                # Skip photos that already have a match for this user
                if UserPhotoMatch.objects.filter(photo=photo, user=user).exists():
                    continue
                    
                try:
                    # Verify face match
                    result = DeepFace.verify(
                        img1_path=reference_image,
                        img2_path=image_path,
                        model_name='VGG-Face',
                        detector_backend='retinaface'
                    )
                    
                    processed_count += 1
                    
                    # If face matches with high confidence
                    if result['verified'] and result.get('distance', 1) < (1 - threshold):
                        matched_count += 1
                        
                        # Create face match
                        confidence = round((1 - result.get('distance', 0)) * 100, 2)
                        UserPhotoMatch.objects.create(
                            photo=photo,
                            user=user,
                            confidence_score=confidence
                        )
                        
                        self.stdout.write(self.style.SUCCESS(f"Matched user to photo {photo.id} with {confidence}% confidence"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing photo {photo.id}: {str(e)}"))
                    continue
                    
                # Print progress every 10 photos
                if processed_count % 10 == 0:
                    self.stdout.write(f"Processed {processed_count} photos, found {matched_count} matches...")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error with photo {photo.id}: {str(e)}"))
                continue
                
        self.stdout.write(self.style.SUCCESS(f"\nComplete! Processed {processed_count} photos"))
        self.stdout.write(self.style.SUCCESS(f"Found {matched_count} photos matching {user.get_full_name() or user.username}"))
        
    def process_all_users(self, event, threshold, source_folder=None):
        """Process photos for all users with profile pictures in the event"""
        # Get all users with profile pictures for this event
        event_users = User.objects.filter(
            Q(organized_events=event) | 
            Q(crew_memberships__event=event) |
            Q(event_attendances__event=event)
        ).distinct()
        
        user_count = 0
        
        for user in event_users:
            if hasattr(user, 'profile_picture') and user.profile_picture:
                user_count += 1
                reference_image = os.path.join(settings.MEDIA_ROOT, str(user.profile_picture))
                
                self.stdout.write(f"\nProcessing for user: {user.get_full_name() or user.username}")
                
                if source_folder:
                    self.process_external_photos(user, event, reference_image, source_folder, threshold)
                else:
                    self.process_event_photos(user, event, reference_image, threshold)
                    
        if user_count == 0:
            self.stdout.write(self.style.WARNING("No users with profile pictures found for this event"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Completed processing for {user_count} users"))