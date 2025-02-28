# tasks.py
import os
import cv2
import face_recognition
import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from celery import shared_task
from PIL import Image, ImageEnhance, ImageFilter
import logging

from .models import EventPhoto, UserPhotoMatch
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError


logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, max_retries=3, default_retry_delay=300)  # 5 minutes retry delay
def process_photo(self, photo_id):
    """Process a photo with AI to detect faces, analyze content, and enhance quality."""
    logger.info(f"Starting to process photo {photo_id}")
    try:
        photo = EventPhoto.objects.get(id=photo_id)
        logger.info(f"Found photo: {photo}")
        
        # Skip if already processed
        if photo.processed:
            logger.info(f"Photo {photo_id} already processed, skipping")
            return
        
        # Load image for processing
        image_path = photo.image.path
        logger.info(f"Image path: {image_path}")
        
        image = cv2.imread(image_path)
        
        if image is None:
            logger.error(f"Failed to load image at {image_path}")
            return
        
        logger.info(f"Successfully loaded image with shape {image.shape}")
        
        # 1. Analyze image quality
        try:
            quality_score = analyze_image_quality(image)
            logger.info(f"Quality score: {quality_score}")
        except Exception as e:
            logger.error(f"Error analyzing image quality: {str(e)}", exc_info=True)
            quality_score = 0.5
        
        # 2. Detect and analyze faces
        try:
            detected_faces = detect_faces(image, photo)
            logger.info(f"Detected faces: {len(detected_faces)}")
        except Exception as e:
            logger.error(f"Error detecting faces: {str(e)}", exc_info=True)
            detected_faces = []
        
        # 3. Generate scene tags based on event type and content
        try:
            scene_tags = generate_tags(image, photo.event.event_type)
            logger.info(f"Generated tags: {scene_tags}")
        except Exception as e:
            logger.error(f"Error generating tags: {str(e)}", exc_info=True)
            scene_tags = []
        
        # 4. Update the photo model with processing results
        photo.processed = True
        photo.quality_score = quality_score
        photo.detected_faces = detected_faces
        photo.scene_tags = scene_tags
        photo.save()
        logger.info(f"Updated photo with processing results")
        
        # 5. Create enhanced version if quality is below threshold
        if quality_score < 0.7:  # Threshold can be adjusted
            try:
                enhance_photo(photo)
                logger.info(f"Enhanced photo created")
            except Exception as e:
                logger.error(f"Error enhancing photo: {str(e)}", exc_info=True)
            
        logger.info(f"Successfully processed photo {photo_id}")
        
    except Exception as e:
        logger.error(f"Error processing photo {photo_id}: {str(e)}", exc_info=True)
        try:
            # Retry the task
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for photo {photo_id}")


def analyze_image_quality(image):
    """Analyze image quality metrics and return a score from 0-1."""
    try:
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate sharpness using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(laplacian_var / 1000, 1.0)  # Normalize to 0-1
        
        # Calculate brightness
        brightness = np.mean(gray) / 255.0
        
        # Calculate contrast
        contrast = np.std(gray) / 128.0
        
        # Combined quality score (with weights)
        quality_score = (0.5 * sharpness_score + 0.25 * (1 - abs(0.5 - brightness) * 2) + 
                         0.25 * min(contrast, 1.0))
        
        return round(quality_score, 2)
    
    except Exception as e:
        logger.error(f"Error analyzing image quality: {str(e)}")
        return 0.5  # Default middle score on error


def detect_faces(image, photo):
    """Detect faces in the image and match with users."""
    try:
        # Convert BGR (OpenCV) to RGB (face_recognition)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Find all faces in the image
        face_locations = face_recognition.face_locations(rgb_image)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        # Prepare result
        face_results = []
        
        # Get all users with profile pictures for this event
        event_users = list(User.objects.filter(
            Q(organized_events=photo.event) | 
            Q(crew_memberships__event=photo.event) |
            Q(event_attendances__event=photo.event)
        ).distinct())
        
        # Create a list of face encodings for users with profile pictures
        user_face_encodings = []
        users_with_faces = []
        
        for user in event_users:
            # Check if user has a profile picture
            if hasattr(user, 'profile_picture') and user.profile_picture:
                profile_pic_path = os.path.join(settings.MEDIA_ROOT, str(user.profile_picture))
                if os.path.exists(profile_pic_path):
                    # Load user profile image and find face encoding
                    user_image = face_recognition.load_image_file(profile_pic_path)
                    user_face_encoding = face_recognition.face_encodings(user_image)
                    
                    if user_face_encoding:  # If a face was found in the profile pic
                        user_face_encodings.append(user_face_encoding[0])
                        users_with_faces.append(user)
        
        # Process detected faces
        for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
            # Initialize face data
            face_data = {
                "position": {
                    "top": face_location[0],
                    "right": face_location[1],
                    "bottom": face_location[2],
                    "left": face_location[3]
                },
                "user_id": None,
                "confidence": None
            }
            
            # Skip matching if no user face encodings
            if not user_face_encodings:
                face_results.append(face_data)
                continue
            
            # Compare face with all user faces
            face_distances = face_recognition.face_distance(user_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                best_match_distance = face_distances[best_match_index]
                
                # If distance is small enough, it's a match (lower is better, threshold of 0.6)
                if best_match_distance < 0.6:
                    matched_user = users_with_faces[best_match_index]
                    confidence = round((1 - best_match_distance) * 100, 2)
                    
                    face_data["user_id"] = matched_user.id
                    face_data["confidence"] = confidence
                    
                    # Create UserPhotoMatch entry
                    UserPhotoMatch.objects.create(
                        photo=photo,
                        user=matched_user,
                        confidence_score=confidence
                    )
            
            face_results.append(face_data)
        
        return face_results
    
    except Exception as e:
        logger.error(f"Error detecting faces: {str(e)}")
        return []


def generate_tags(image, event_type):
    """Generate tags based on image content and event type."""
    # Note: In a production environment, you would integrate with a computer vision 
    # API like Google Vision, Azure Computer Vision, or use a pre-trained model
    
    # Simple placeholder implementation - this would be replaced with actual ML model
    tags = []
    
    # 1. Add event type as a tag
    if event_type:
        tags.append(event_type.lower())
    
    # 2. Basic color analysis for scene detection
    try:
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Check if it's likely an outdoor scene (analyzing blue sky presence)
        h_channel, s_channel, v_channel = cv2.split(hsv_image)
        blue_mask = cv2.inRange(hsv_image, (100, 50, 50), (130, 255, 255))
        blue_ratio = cv2.countNonZero(blue_mask) / (image.shape[0] * image.shape[1])
        
        if blue_ratio > 0.15:
            tags.append("outdoor")
        else:
            tags.append("indoor")
        
        # 3. Check for specific lighting conditions
        if np.mean(v_channel) < 75:
            tags.append("dark")
        elif np.mean(v_channel) > 200:
            tags.append("bright")
    except Exception as e:
        logger.error(f"Error in color analysis: {str(e)}")
        # Add default tags if color analysis fails
        tags.append("indoor")
    
    # Rest of the function remains the same...
    
    return list(set(tags))  # Remove duplicates


def enhance_photo(photo):
    """Create an enhanced version of a low-quality photo."""
    try:
        # Open the image with PIL
        image_path = photo.image.path
        img = Image.open(image_path)
        
        # Get the directory and filename
        directory, filename = os.path.split(image_path)
        base_name, extension = os.path.splitext(filename)
        
        # Create the directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        enhanced_filename = f"{base_name}_enhanced{extension}"
        enhanced_path = os.path.join(directory, enhanced_filename)
        
        # Apply enhancements
        img = ImageEnhance.Contrast(img).enhance(1.2)  # Increase contrast
        img = ImageEnhance.Brightness(img).enhance(1.1)  # Slight brightness boost
        img = ImageEnhance.Sharpness(img).enhance(1.5)  # Sharpen
        
        # Save the enhanced image
        img.save(enhanced_path)
        
        # Update the photo model with enhanced image path
        relative_path = os.path.relpath(enhanced_path, settings.MEDIA_ROOT)
        photo.enhanced_image = relative_path
        photo.save(update_fields=['enhanced_image'])
        
    except Exception as e:
        logger.error(f"Error enhancing photo: {str(e)}")

    
@shared_task
def test_task():
    logger.info("Running test task")
    return "Task completed successfully"