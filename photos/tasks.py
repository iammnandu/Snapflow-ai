# tasks.py
import os
import cv2
import face_recognition
import numpy as np
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from celery import shared_task, chord, group # type: ignore
from PIL import Image, ImageEnhance, ImageFilter
import logging
from scipy.spatial.distance import cosine # type: ignore
import tempfile
from pathlib import Path
import shutil
import concurrent.futures
from functools import partial

from .models import EventPhoto, UserPhotoMatch
from celery.exceptions import MaxRetriesExceededError # type: ignore

# Add this import at the top of tasks.py
from deepface import DeepFace # type: ignore

logger = logging.getLogger(__name__)
User = get_user_model()

# Cache for user encodings to avoid repeated processing
USER_ENCODING_CACHE = {}

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
        
        # Run tasks in parallel using chord
        # First group of tasks: quality analysis, face detection, tag generation
        analysis_tasks = group([
            analyze_image_quality_task.s(image_path),
            detect_faces_optimized.s(image_path, photo_id),
            generate_tags_task.s(image_path, photo.event.event_type if hasattr(photo.event, 'event_type') else None)
        ])
        
        # Callback task to update the photo with results
        callback = process_photo_results.s(photo_id)
        
        # Execute the chord
        chord(analysis_tasks)(callback)
        
        logger.info(f"Started parallel processing tasks for photo {photo_id}")
        return
        
    except Exception as e:
        logger.error(f"Error processing photo {photo_id}: {str(e)}", exc_info=True)
        try:
            # Retry the task
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for photo {photo_id}")


@shared_task
def analyze_image_quality_task(image_path):
    """Task to analyze image quality."""
    try:
        image = cv2.imread(image_path)
        quality_score = analyze_image_quality(image)
        logger.info(f"Quality score for {image_path}: {quality_score}")
        return quality_score
    except Exception as e:
        logger.error(f"Error analyzing image quality for {image_path}: {str(e)}")
        return 0.5


@shared_task
def generate_tags_task(image_path, event_type):
    """Task to generate image tags."""
    try:
        image = cv2.imread(image_path)
        tags = generate_tags(image, event_type)
        logger.info(f"Generated tags for {image_path}: {tags}")
        return tags
    except Exception as e:
        logger.error(f"Error generating tags for {image_path}: {str(e)}")
        return []


@shared_task
def process_photo_results(results, photo_id):
    """Process and save the results from parallel tasks."""
    try:
        photo = EventPhoto.objects.get(id=photo_id)
        
        # Unpack results
        quality_score = results[0]
        detected_faces = results[1]
        scene_tags = results[2]
        
        # Update the photo model with processing results
        photo.processed = True
        photo.quality_score = quality_score
        photo.detected_faces = detected_faces
        photo.scene_tags = scene_tags
        photo.save()
        logger.info(f"Updated photo {photo_id} with processing results")
        
        # Create enhanced version if quality is below threshold
        if quality_score < 0.7:  # Threshold can be adjusted
            enhance_photo_task.delay(photo_id)
        
        return "Photo processing completed successfully"
        
    except Exception as e:
        logger.error(f"Error processing results for photo {photo_id}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


@shared_task
def enhance_photo_task(photo_id):
    """Task to create an enhanced version of a photo."""
    try:
        photo = EventPhoto.objects.get(id=photo_id)
        enhance_photo(photo)
        logger.info(f"Enhanced photo {photo_id} created")
        return "Photo enhancement completed"
    except Exception as e:
        logger.error(f"Error enhancing photo {photo_id}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"


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
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization to improve contrast
        equalized = cv2.equalizeHist(gray)
        
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


def preprocess_event_users(event_id):
    """Preprocess and cache user profile pictures and encodings for an event."""
    try:
        # Get all users with profile pictures for this event
        event_users = list(User.objects.filter(
            Q(organized_events__id=event_id) | 
            Q(eventcrew__event__id=event_id) |
            Q(eventparticipant__event__id=event_id)
        ).distinct())
        
        logger.info(f"Preprocessing profile pictures for {len(event_users)} event users")
        
        # Create a temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create debug directory
            debug_dir = os.path.join(settings.MEDIA_ROOT, 'debug_faces')
            os.makedirs(debug_dir, exist_ok=True)
            
            # Dictionary to store user data
            user_data = {}
            
            # Process users in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # Create a partial function with the temp_dir parameter
                process_user_func = partial(preprocess_user, temp_dir=temp_dir, debug_dir=debug_dir)
                
                # Process all users
                future_to_user = {executor.submit(process_user_func, user): user for user in event_users}
                
                # Collect results
                for future in concurrent.futures.as_completed(future_to_user):
                    user = future_to_user[future]
                    try:
                        result = future.result()
                        if result:
                            user_data[user.id] = result
                    except Exception as e:
                        logger.error(f"Error preprocessing user {user.username}: {str(e)}")
            
            logger.info(f"Preprocessed {len(user_data)} users successfully")
            return user_data
    
    except Exception as e:
        logger.error(f"Error preprocessing event users: {str(e)}")
        return {}


def preprocess_user(user, temp_dir, debug_dir):
    """Process a single user's profile picture."""
    try:
        # Check if user has an avatar picture
        if hasattr(user, 'avatar') and user.avatar:
            profile_pic_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
            
            if os.path.exists(profile_pic_path):
                # Save a copy of profile pic for debugging
                debug_profile_path = os.path.join(debug_dir, f"user_{user.id}_profile.jpg")
                shutil.copy(profile_pic_path, debug_profile_path)
                
                # Preprocess the profile picture
                processed_profile_path = os.path.join(temp_dir, f"user_{user.id}_profile_processed.jpg")
                preprocessed_profile = preprocess_image(profile_pic_path, processed_profile_path)
                
                # Load user encoding for face_recognition library
                profile_img = face_recognition.load_image_file(preprocessed_profile)
                face_locations = face_recognition.face_locations(profile_img)
                
                if face_locations:
                    # Get face encodings
                    face_encoding = face_recognition.face_encodings(profile_img, [face_locations[0]])[0]
                    
                    # Extract face from profile picture for DeepFace
                    profile_faces = DeepFace.extract_faces(
                        img_path=preprocessed_profile,
                        detector_backend='retinaface',
                        enforce_detection=False
                    )
                    
                    if profile_faces:
                        # Get face region
                        profile_face = profile_faces[0]
                        profile_face_img = cv2.imread(preprocessed_profile)
                        
                        extracted_profile_face = profile_face_img[
                            int(profile_face['facial_area']['y']):int(profile_face['facial_area']['y'] + profile_face['facial_area']['h']),
                            int(profile_face['facial_area']['x']):int(profile_face['facial_area']['x'] + profile_face['facial_area']['w'])
                        ]
                        
                        extracted_profile_path = os.path.join(temp_dir, f"user_{user.id}_face.jpg")
                        cv2.imwrite(extracted_profile_path, extracted_profile_face)
                        
                        # Create representations for all DeepFace models
                        deepface_reps = {}
                        for model_name in ['Facenet', 'VGG-Face', 'ArcFace']:
                            try:
                                # Get embedding
                                embedding_obj = DeepFace.represent(
                                    img_path=extracted_profile_path,
                                    model_name=model_name,
                                    detector_backend='skip'
                                )
                                deepface_reps[model_name] = embedding_obj[0]['embedding']
                            except Exception as e:
                                logger.error(f"Error creating {model_name} representation for user {user.username}: {str(e)}")
                        
                        # Return user data with encodings
                        return {
                            'face_recognition_encoding': face_encoding,
                            'deepface_representations': deepface_reps,
                            'profile_pic_path': profile_pic_path,
                            'extracted_face_path': extracted_profile_path
                        }
    
    except Exception as e:
        logger.error(f"Error preprocessing user {user.username}: {str(e)}")
    
    return None


@shared_task
def detect_faces_optimized(image_path, photo_id):
    """Optimized face detection that processes all faces and users in parallel."""
    try:
        photo = EventPhoto.objects.get(id=photo_id)
        image = cv2.imread(image_path)
        
        if image is None:
            logger.error(f"Failed to load image at {image_path}")
            return []
        
        logger.info(f"Optimized face detection for photo {photo_id}")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Preprocess the image for better detection
            preprocessed_image_path = os.path.join(temp_dir, "preprocessed_main.jpg")
            preprocess_image(image_path, preprocessed_image_path)
            
            # 1. First detect all faces in the image using RetinaFace (faster than DeepFace.extract_faces)
            try:
                # Use DeepFace to detect faces in the image
                detected_faces = DeepFace.extract_faces(
                    img_path=preprocessed_image_path,
                    detector_backend='retinaface',
                    enforce_detection=False  # Don't error if no faces detected
                )
                
                if not detected_faces:
                    logger.warning(f"No faces detected in photo {photo_id}")
                    return []
                
                logger.info(f"Detected {len(detected_faces)} faces in photo {photo_id}")
                
                # Extract faces and save them
                face_images = []
                face_objects = []
                
                # Create debug directory
                debug_dir = os.path.join(settings.MEDIA_ROOT, 'debug_faces')
                os.makedirs(debug_dir, exist_ok=True)
                
                for i, face_data in enumerate(detected_faces):
                    # Create face object
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
                    
                    # Skip very small faces
                    if face_img.shape[0] < 20 or face_img.shape[1] < 20:
                        logger.warning(f"Skipping very small face {i} in photo {photo_id}")
                        continue
                    
                    # Align face using landmarks
                    aligned_face = align_face(face_img)
                    
                    # Save aligned face for processing
                    face_path = os.path.join(temp_dir, f"face_{i}.jpg")
                    cv2.imwrite(face_path, aligned_face)
                    
                    # Save a copy for debugging
                    debug_face_path = os.path.join(debug_dir, f"photo_{photo.id}_face_{i}.jpg")
                    cv2.imwrite(debug_face_path, aligned_face)
                    
                    # Store face data
                    face_images.append({
                        'index': i,
                        'path': face_path,
                        'aligned_face': aligned_face
                    })
                    face_objects.append(face_obj)
                
                # 2. Preprocess all user profile pictures for the event (if not already cached)
                event_id = photo.event.id
                
                # Check if users for this event are already preprocessed
                if event_id not in USER_ENCODING_CACHE:
                    logger.info(f"Preprocessing event {event_id} users")
                    USER_ENCODING_CACHE[event_id] = preprocess_event_users(event_id)
                
                event_users_data = USER_ENCODING_CACHE[event_id]
                logger.info(f"Using cached data for {len(event_users_data)} users in event {event_id}")
                
                # 3. Generate face representations for all detected faces
                face_representations = []
                for face_data in face_images:
                    face_index = face_data['index']
                    face_path = face_data['path']
                    
                    # Generate face recognition encoding
                    fr_image = face_recognition.load_image_file(face_path)
                    fr_encoding = None
                    try:
                        fr_encoding = face_recognition.face_encodings(fr_image)[0]
                    except IndexError:
                        logger.warning(f"face_recognition couldn't generate encoding for face {face_index}")
                    
                    # Generate DeepFace representations
                    df_representations = {}
                    for model_name in ['Facenet', 'VGG-Face', 'ArcFace']:
                        try:
                            embedding_obj = DeepFace.represent(
                                img_path=face_path,
                                model_name=model_name,
                                detector_backend='skip'
                            )
                            df_representations[model_name] = embedding_obj[0]['embedding']
                        except Exception as e:
                            logger.error(f"Error creating {model_name} representation for face {face_index}: {str(e)}")
                    
                    face_representations.append({
                        'index': face_index,
                        'face_recognition_encoding': fr_encoding,
                        'deepface_representations': df_representations
                    })
                
                # 4. Match faces with users in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as executor:
                    # Create a partial function with fixed parameters
                    match_func = partial(
                        match_face_with_users, 
                        event_users_data=event_users_data
                    )
                    
                    # Submit all face matching tasks
                    future_to_face = {executor.submit(match_func, face_rep): face_rep['index'] for face_rep in face_representations}
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_face):
                        face_index = future_to_face[future]
                        try:
                            match_result = future.result()
                            if match_result:
                                # Update the corresponding face object with match data
                                for i, face_obj in enumerate(face_objects):
                                    if i == face_index:
                                        face_obj['user_id'] = match_result['user_id']
                                        face_obj['confidence'] = match_result['confidence']
                                        face_obj['matched_by'] = match_result['matched_by']
                                        
                                        # Create UserPhotoMatch entry
                                        UserPhotoMatch.objects.create(
                                            photo=photo,
                                            user=User.objects.get(id=match_result['user_id']),
                                            confidence_score=match_result['confidence'],
                                            method=match_result['matched_by']
                                        )
                                        break
                        except Exception as e:
                            logger.error(f"Error processing match result for face {face_index}: {str(e)}")
                
                # Log results
                matches_found = sum(1 for face in face_objects if face.get('user_id') is not None)
                logger.info(f"Found {matches_found} matches out of {len(face_objects)} faces")
                return face_objects
                
            except Exception as e:
                logger.error(f"Error in optimized face detection: {str(e)}")
                return []
    
    except Exception as e:
        logger.error(f"Error in detect_faces_optimized: {str(e)}", exc_info=True)
        return []


def match_face_with_users(face_rep, event_users_data):
    """Match a single face with all event users in parallel."""
    try:
        face_index = face_rep['index']
        fr_encoding = face_rep['face_recognition_encoding']
        df_representations = face_rep['deepface_representations']
        
        logger.info(f"Matching face {face_index} with {len(event_users_data)} users")
        
        # Track best match across all methods
        best_match = None
        best_confidence = 0
        best_method = None
        
        # Try DeepFace matching first (usually more accurate)
        for model_name, face_embedding in df_representations.items():
            if not face_embedding:
                continue
                
            # Match against all users with this model
            for user_id, user_data in event_users_data.items():
                if not user_data:
                    continue
                    
                user_df_reps = user_data.get('deepface_representations', {})
                user_embedding = user_df_reps.get(model_name)
                
                if user_embedding:
                    try:
                        # Calculate distance
                        distance = cosine(np.array(face_embedding), np.array(user_embedding))
                        confidence = (1 - distance) * 100
                        
                        # Threshold varies by model
                        threshold = 50  # Default
                        if model_name == 'Facenet':
                            threshold = 45
                        elif model_name == 'VGG-Face':
                            threshold = 55
                        elif model_name == 'ArcFace':
                            threshold = 50
                            
                        if confidence > threshold and confidence > best_confidence:
                            best_confidence = confidence
                            best_match = user_id
                            best_method = f"deepface_{model_name}"
                    except Exception as e:
                        logger.error(f"Error matching face {face_index} with user {user_id} using {model_name}: {str(e)}")
        
        # Try face_recognition as fallback
        if fr_encoding is not None and (best_match is None or best_confidence < 60):
            for user_id, user_data in event_users_data.items():
                if not user_data:
                    continue
                    
                user_fr_encoding = user_data.get('face_recognition_encoding')
                
                if user_fr_encoding is not None:
                    try:
                        # Calculate face distance
                        face_distance = face_recognition.face_distance([user_fr_encoding], fr_encoding)[0]
                        confidence = (1 - face_distance) * 100
                        
                        if confidence > 45 and confidence > best_confidence:
                            best_confidence = confidence
                            best_match = user_id
                            best_method = "face_recognition"
                    except Exception as e:
                        logger.error(f"Error matching face {face_index} with user {user_id} using face_recognition: {str(e)}")
        
        # Return the best match if found
        if best_match:
            return {
                'user_id': best_match,
                'confidence': round(best_confidence, 2),
                'matched_by': best_method
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error in match_face_with_users: {str(e)}")
        return None


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


# Helper task to clear the user encoding cache for an event
@shared_task
def clear_user_encoding_cache(event_id=None):
    """Clear the user encoding cache for a specific event or all events."""
    global USER_ENCODING_CACHE
    if event_id:
        if event_id in USER_ENCODING_CACHE:
            del USER_ENCODING_CACHE[event_id]
            logger.info(f"Cleared user encoding cache for event {event_id}")
    else:
        USER_ENCODING_CACHE = {}
        logger.info("Cleared all user encoding cache")
    return "Cache cleared"

