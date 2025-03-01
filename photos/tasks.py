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
from scipy.spatial.distance import cosine
import tempfile
from pathlib import Path
import shutil

from .models import EventPhoto, UserPhotoMatch
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

# Add this import at the top of tasks.py
from deepface import DeepFace

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
        
        # 2. Detect and analyze faces using enhanced method with multiple backends
        try:
            detected_faces = detect_faces_with_fallback(image, photo)
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


def preprocess_image(img_path, output_path=None):
    """Preprocess images to improve face recognition accuracy."""
    try:
        img = cv2.imread(img_path)
        if img is None:
            logger.error(f"Failed to load image at {img_path}")
            return img_path
            
        # Apply preprocessing steps
        # 1. Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 2. Apply histogram equalization to improve contrast
        equalized = cv2.equalizeHist(gray)
        
        # 3. Apply Gaussian blur to reduce noise (optional)
        # blurred = cv2.GaussianBlur(equalized, (5, 5), 0)
        
        # 4. Apply adaptive thresholding to enhance features (optional)
        # thresh = cv2.adaptiveThreshold(equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        #                               cv2.THRESH_BINARY, 11, 2)
        
        # Determine output path
        if output_path is None:
            output_path = img_path.replace('.jpg', '_preprocessed.jpg')
            output_path = output_path.replace('.png', '_preprocessed.png')
            
        # Save preprocessed image
        cv2.imwrite(output_path, equalized)
        logger.info(f"Preprocessed image saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error preprocessing image {img_path}: {str(e)}")
        return img_path  # Return original path if preprocessing fails


def align_face(face_img):
    """Align face using facial landmarks."""
    try:
        # Convert to RGB for face_recognition
        rgb_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Detect landmarks
        face_landmarks_list = face_recognition.face_landmarks(rgb_face)
        
        if not face_landmarks_list:
            logger.warning("No landmarks detected for face alignment")
            return face_img
            
        landmarks = face_landmarks_list[0]
        
        # Get eye coordinates
        left_eye = np.mean(np.array(landmarks['left_eye']), axis=0).astype(int)
        right_eye = np.mean(np.array(landmarks['right_eye']), axis=0).astype(int)
        
        # Calculate angle
        dY = right_eye[1] - left_eye[1]
        dX = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dY, dX))
        
        # Get the center of the image
        (h, w) = face_img.shape[:2]
        center = (w // 2, h // 2)
        
        # Get rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Apply rotation
        aligned_face = cv2.warpAffine(face_img, M, (w, h), flags=cv2.INTER_CUBIC)
        
        return aligned_face
        
    except Exception as e:
        logger.error(f"Error aligning face: {str(e)}")
        return face_img  # Return original face if alignment fails


def detect_faces_with_fallback(image, photo):
    """Enhanced face detection with multiple backends and fallbacks."""
    try:
        # First try with DeepFace
        deepface_results = detect_faces_deepface(image, photo)
        
        # Count matches found with DeepFace
        deepface_matches = sum(1 for face in deepface_results if face.get('user_id') is not None)
        logger.info(f"DeepFace found {deepface_matches} matches out of {len(deepface_results)} faces")
        
        # If DeepFace didn't find all matches, try face_recognition library
        if deepface_matches < len(deepface_results):
            logger.info("Some faces not matched with DeepFace, trying face_recognition library")
            face_recognition_results = detect_faces_face_recognition(image, photo)
            
            # Merge results - use face_recognition results for faces without matches
            for i, face in enumerate(deepface_results):
                if face.get('user_id') is None and i < len(face_recognition_results):
                    if face_recognition_results[i].get('user_id') is not None:
                        logger.info(f"Face {i+1} matched by face_recognition but not DeepFace")
                        deepface_results[i]['user_id'] = face_recognition_results[i]['user_id']
                        deepface_results[i]['confidence'] = face_recognition_results[i]['confidence']
                        deepface_results[i]['matched_by'] = 'face_recognition'
                        
                        # Create UserPhotoMatch entry
                        UserPhotoMatch.objects.create(
                            photo=photo,
                            user=User.objects.get(id=face_recognition_results[i]['user_id']),
                            confidence_score=face_recognition_results[i]['confidence'],
                            method='face_recognition'
                        )
        
        # Final count of matches
        final_matches = sum(1 for face in deepface_results if face.get('user_id') is not None)
        logger.info(f"Final result: {final_matches} matches out of {len(deepface_results)} faces")
        
        return deepface_results
        
    except Exception as e:
        logger.error(f"Error in enhanced face detection: {str(e)}")
        return []


def detect_faces_deepface(image, photo):
    """Detect faces in the image and match with users using DeepFace."""
    try:
        # Save the OpenCV image to a temporary file for DeepFace to process
        image_path = photo.image.path

        logger.info(f"Photo image path: {photo.image.path}")
        logger.info(f"Path exists: {os.path.exists(photo.image.path)}")

        # Log event participants statistics
        organizers = User.objects.filter(organized_events=photo.event).count()
        crew = User.objects.filter(eventcrew__event=photo.event).count()
        participants = User.objects.filter(eventparticipant__event=photo.event).count()
        total = User.objects.filter(
            Q(organized_events=photo.event) | 
            Q(eventcrew__event=photo.event) |
            Q(eventparticipant__event=photo.event)
        ).distinct().count()

        logger.info(f"Organizers: {organizers}, Crew: {crew}, Participants: {participants}, Total unique: {total}")

        # Get all users with profile pictures for this event
        event_users = list(User.objects.filter(
            Q(organized_events=photo.event) | 
            Q(eventcrew__event=photo.event) |
            Q(eventparticipant__event=photo.event)
        ).distinct())
        
        face_results = []
        
        # Create directories for debug
        debug_dir = os.path.join(settings.MEDIA_ROOT, 'debug_faces')
        os.makedirs(debug_dir, exist_ok=True)
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # First, detect faces in the photo
            try:
                # Preprocess the main image for better face detection
                preprocessed_image_path = os.path.join(temp_dir, "preprocessed_main.jpg")
                preprocess_image(image_path, preprocessed_image_path)
                
                # Use DeepFace to detect faces in the image
                detected_faces = DeepFace.extract_faces(
                    img_path=preprocessed_image_path,
                    detector_backend='retinaface',
                    enforce_detection=False  # Don't error if no faces detected
                )
                
                # Process each detected face
                for i, face_data in enumerate(detected_faces):
                    face_obj = {
                        "position": {
                            "top": int(face_data['facial_area']['y']),
                            "right": int(face_data['facial_area']['x'] + face_data['facial_area']['w']),
                            "bottom": int(face_data['facial_area']['y'] + face_data['facial_area']['h']),
                            "left": int(face_data['facial_area']['x'])
                        },
                        "user_id": None,
                        "confidence": None,
                        "matched_by": None
                    }
                    
                    # Get face region 
                    face_img = image[
                        face_obj["position"]["top"]:face_obj["position"]["bottom"],
                        face_obj["position"]["left"]:face_obj["position"]["right"]
                    ]
                    
                    # Align face using landmarks
                    aligned_face = align_face(face_img)
                    
                    # Save aligned face for processing
                    face_path = os.path.join(temp_dir, f"face_{i}.jpg")
                    cv2.imwrite(face_path, aligned_face)
                    
                    # Save a copy for debugging
                    debug_face_path = os.path.join(debug_dir, f"photo_{photo.id}_face_{i}.jpg")
                    cv2.imwrite(debug_face_path, aligned_face)
                    
                    # Analyze face quality
                    face_quality = analyze_image_quality(aligned_face)
                    logger.info(f"Face {i+1} quality: {face_quality}")
                    
                    # Try to match with users using multiple models
                    best_match_user = None
                    best_match_confidence = 0
                    best_match_model = None
                    
                    # These models are available in DeepFace
                    models = ['Facenet', 'VGG-Face', 'ArcFace', 'Dlib']
                    
                    logger.info(f"Number of event users found: {len(event_users)}")
                    for user in event_users:
                        logger.info(f"User: {user.username}, has avatar: {hasattr(user, 'avatar') and bool(user.avatar)}")
                        
                        # Check if user has an avatar picture
                        if hasattr(user, 'avatar') and user.avatar:
                            profile_pic_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
                            logger.info(f"User {user.username} avatar path: {profile_pic_path}")
                            logger.info(f"Avatar exists: {os.path.exists(profile_pic_path)}")
                            
                            if os.path.exists(profile_pic_path):
                                # Save a copy of profile pic for debugging
                                debug_profile_path = os.path.join(debug_dir, f"user_{user.id}_profile.jpg")
                                shutil.copy(profile_pic_path, debug_profile_path)
                                
                                # Preprocess the profile picture
                                processed_profile_path = os.path.join(temp_dir, f"user_{user.id}_profile_processed.jpg")
                                preprocessed_profile = preprocess_image(profile_pic_path, processed_profile_path)
                                
                                # Try different models for verification
                                for model_name in models:
                                    try:
                                        # First extract face from profile pic to ensure proper comparison
                                        profile_faces = DeepFace.extract_faces(
                                            img_path=preprocessed_profile,
                                            detector_backend='retinaface',
                                            enforce_detection=False
                                        )
                                        
                                        if not profile_faces:
                                            logger.warning(f"No face detected in profile picture for user {user.username}")
                                            continue
                                            
                                        # Extract and save the face from profile pic
                                        profile_face = profile_faces[0]
                                        profile_face_img = cv2.imread(preprocessed_profile)
                                        extracted_profile_face = profile_face_img[
                                            int(profile_face['facial_area']['y']):int(profile_face['facial_area']['y'] + profile_face['facial_area']['h']),
                                            int(profile_face['facial_area']['x']):int(profile_face['facial_area']['x'] + profile_face['facial_area']['w'])
                                        ]
                                        
                                        extracted_profile_path = os.path.join(temp_dir, f"user_{user.id}_face.jpg")
                                        cv2.imwrite(extracted_profile_path, extracted_profile_face)
                                        
                                        # Now verify with the extracted faces
                                        result = DeepFace.verify(
                                            img1_path=extracted_profile_path,
                                            img2_path=face_path,
                                            model_name=model_name,
                                            detector_backend='skip',  # Skip detection as we already have faces
                                            distance_metric='cosine'
                                        )
                                        
                                        # Calculate confidence (1 - distance)
                                        distance = result.get('distance', 0)
                                        confidence = (1 - distance) * 100
                                        
                                        # Log verification attempts
                                        if result['verified']:
                                            logger.info(f"Match: User {user.username} matched with confidence {confidence:.2f}% using {model_name}")
                                        else:
                                            logger.info(f"No match: User {user.username}, distance: {distance:.4f} using {model_name}")
                                        
                                        # Update best match if this is better
                                        if result['verified'] and confidence > best_match_confidence:
                                            # Adjust the threshold based on model
                                            threshold = 50  # Default
                                            if model_name == 'Facenet':
                                                threshold = 45
                                            elif model_name == 'VGG-Face':
                                                threshold = 55
                                            elif model_name == 'ArcFace':
                                                threshold = 50
                                            elif model_name == 'Dlib':
                                                threshold = 45
                                                
                                            if confidence > threshold:
                                                best_match_confidence = confidence
                                                best_match_user = user
                                                best_match_model = model_name
                                    
                                    except Exception as e:
                                        logger.error(f"Error matching with model {model_name} for user {user.username}: {str(e)}")
                                        continue
                    
                    # If we found a match, add user info
                    if best_match_user:
                        face_obj["user_id"] = best_match_user.id
                        face_obj["confidence"] = round(best_match_confidence, 2)
                        face_obj["matched_by"] = f"deepface_{best_match_model}"
                        
                        # Create UserPhotoMatch entry
                        UserPhotoMatch.objects.create(
                            photo=photo,
                            user=best_match_user,
                            confidence_score=face_obj["confidence"],
                            method=f"deepface_{best_match_model}"
                        )
                    
                    face_results.append(face_obj)
                
                logger.info(f"DeepFace face matches found: {sum(1 for face in face_results if face.get('user_id') is not None)}")
                
            except Exception as e:
                logger.error(f"Error in DeepFace face detection: {str(e)}")
        
        return face_results
    
    except Exception as e:
        logger.error(f"Error in DeepFace detection: {str(e)}")
        return []


def detect_faces_face_recognition(image, photo):
    """Use face_recognition library as an alternative method."""
    face_results = []
    try:
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get RGB image for face_recognition library
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find all faces in the image
            face_locations = face_recognition.face_locations(rgb_image)
            
            if not face_locations:
                logger.warning("No faces detected by face_recognition library")
                return []
                
            # Find face encodings
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            # Get all users with profile pictures for this event
            event_users = list(User.objects.filter(
                Q(organized_events=photo.event) | 
                Q(eventcrew__event=photo.event) |
                Q(eventparticipant__event=photo.event)
            ).distinct())
            
            # Create debug directory
            debug_dir = os.path.join(settings.MEDIA_ROOT, 'debug_faces')
            os.makedirs(debug_dir, exist_ok=True)
            
            # Cache user encodings
            user_encodings = {}
            for user in event_users:
                if hasattr(user, 'avatar') and user.avatar:
                    profile_pic_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
                    if os.path.exists(profile_pic_path):
                        try:
                            # Save preprocessed profile pic
                            preprocessed_profile = os.path.join(temp_dir, f"user_{user.id}_profile_preprocessed.jpg")
                            preprocess_image(profile_pic_path, preprocessed_profile)
                            
                            # Load image and get encoding
                            profile_img = face_recognition.load_image_file(preprocessed_profile)
                            profile_encoding = face_recognition.face_encodings(profile_img)
                            
                            if profile_encoding:
                                user_encodings[user.id] = profile_encoding[0]
                                logger.info(f"Created face encoding for user {user.username}")
                        except Exception as e:
                            logger.error(f"Error encoding user {user.username}: {str(e)}")
                            
            # Process each face
            for i, (face_location, face_encoding) in enumerate(zip(face_locations, face_encodings)):
                top, right, bottom, left = face_location
                face_obj = {
                    "position": {
                        "top": top,
                        "right": right,
                        "bottom": bottom,
                        "left": left
                    },
                    "user_id": None,
                    "confidence": None,
                    "matched_by": None
                }
                
                # Extract face for debugging
                face_img = image[top:bottom, left:right]
                debug_face_path = os.path.join(debug_dir, f"photo_{photo.id}_face_recognition_{i}.jpg")
                cv2.imwrite(debug_face_path, face_img)
                
                # Try to match with users
                best_match_user = None
                best_match_confidence = 0
                
                for user_id, user_encoding in user_encodings.items():
                    try:
                        # Compare face encodings
                        face_distance = face_recognition.face_distance([user_encoding], face_encoding)[0]
                        # Convert distance to confidence score (0-100)
                        confidence = (1 - face_distance) * 100
                        
                        user = User.objects.get(id=user_id)
                        logger.info(f"face_recognition: User {user.username}, confidence: {confidence:.2f}%")
                        
                        if confidence > best_match_confidence and confidence > 45:  # Lower threshold than DeepFace
                            best_match_confidence = confidence
                            best_match_user = user
                    except Exception as e:
                        logger.error(f"Error matching face with user {user_id}: {str(e)}")
                        
                # If we found a match, add user info
                if best_match_user:
                    face_obj["user_id"] = best_match_user.id
                    face_obj["confidence"] = round(best_match_confidence, 2)
                    face_obj["matched_by"] = "face_recognition"
                    
                face_results.append(face_obj)
                
            logger.info(f"face_recognition matches found: {sum(1 for face in face_results if face.get('user_id') is not None)}")
                
        return face_results
    
    except Exception as e:
        logger.error(f"Error in face_recognition detection: {str(e)}")
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


# Add a Model class for testing if you don't already have it
# If you already have UserPhotoMatch model, just make sure it has a 'method' field
"""
from django.db import models

class UserPhotoMatch(models.Model):
    photo = models.ForeignKey('EventPhoto', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    confidence_score = models.FloatField()
    method = models.CharField(max_length=100, default='deepface')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('photo', 'user')
"""