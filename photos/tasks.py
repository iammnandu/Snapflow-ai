

import cv2 # type: ignore
import face_recognition  # type: ignore
import numpy as np # type: ignore
from PIL import Image, ImageEnhance, ImageFilter
from scipy.spatial.distance import cosine  # type: ignore
from deepface import DeepFace  # type: ignore

from celery import shared_task, chord, group  # type: ignore
from celery.exceptions import MaxRetriesExceededError  # type: ignore

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import EventPhoto, UserPhotoMatch


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
    """
    Generate tags based on image content and event type.
    Uses multiple detection techniques to provide rich scene understanding.
    """
    import numpy as np
    import cv2
    from sklearn.cluster import KMeans
    import logging

    logger = logging.getLogger(__name__)
    tags = []
    
    # 1. Add event type as a tag
    if event_type:
        tags.append(event_type.lower())
    
    try:
        # 2. Advanced scene analysis
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h_channel, s_channel, v_channel = cv2.split(hsv_image)
        
        # 2.1 Indoor/Outdoor detection
        # Check for sky presence (blue color)
        blue_mask = cv2.inRange(hsv_image, (100, 50, 50), (130, 255, 255))
        blue_ratio = cv2.countNonZero(blue_mask) / (image.shape[0] * image.shape[1])
        
        # Check for green (vegetation)
        green_mask = cv2.inRange(hsv_image, (35, 50, 50), (85, 255, 255))
        green_ratio = cv2.countNonZero(green_mask) / (image.shape[0] * image.shape[1])
        
        # Combined outdoor indicators
        if blue_ratio > 0.15 or green_ratio > 0.2:
            tags.append("outdoor")
            
            # Add nature tags if significant greenery
            if green_ratio > 0.3:
                tags.append("nature")
                
            # Check for beach/water scene
            if blue_ratio > 0.25:
                # Water and sand detection
                sand_mask = cv2.inRange(hsv_image, (20, 10, 180), (40, 60, 255))
                sand_ratio = cv2.countNonZero(sand_mask) / (image.shape[0] * image.shape[1])
                
                if sand_ratio > 0.1:
                    tags.append("beach")
                elif blue_ratio > 0.35:
                    tags.append("water")
        else:
            tags.append("indoor")
            
            # Check for indoor venue characteristics
            # Detect stage/performance setting
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            # Check for strong horizontal/vertical lines (typical in indoor venues)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
            if lines is not None and len(lines) > 10:
                horizontal_lines = 0
                vertical_lines = 0
                
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(y2 - y1) < 20:  # Horizontal line
                        horizontal_lines += 1
                    if abs(x2 - x1) < 20:  # Vertical line
                        vertical_lines += 1
                
                if horizontal_lines > 5 and vertical_lines > 5:
                    tags.append("venue")
        
        # 2.2 Time of day detection
        avg_brightness = np.mean(v_channel)
        if avg_brightness < 70:
            tags.append("night")
            tags.append("dark")
        elif avg_brightness < 120:
            # Check color temperature for sunset/sunrise
            if np.mean(h_channel) > 10 and np.mean(h_channel) < 30:
                tags.append("sunset")
            else:
                tags.append("dim")
        elif avg_brightness > 200:
            tags.append("bright")
        
        # 2.3 Color palette analysis
        # Resize image for faster processing
        small_image = cv2.resize(image, (100, 100))
        pixels = small_image.reshape(-1, 3)
        
        # Extract dominant colors using K-means
        kmeans = KMeans(n_clusters=3)
        kmeans.fit(pixels)
        dominant_colors = kmeans.cluster_centers_
        
        # Check for vibrant colors
        saturation_values = []
        for color in dominant_colors:
            b, g, r = color
            color_hsv = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0][0]
            saturation_values.append(color_hsv[1])
        
        avg_saturation = np.mean(saturation_values)
        if avg_saturation > 150:
            tags.append("colorful")
        elif avg_saturation < 70:
            tags.append("muted")
        
        # 2.4 Detect crowd density
        # Use face detection to approximate crowd
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) > 10:
            tags.append("crowd")
        elif len(faces) > 5:
            tags.append("group")
        elif len(faces) > 0:
            tags.append("people")
        
        # 2.5 Context-specific tags based on event_type
        if event_type:
            event_type_lower = event_type.lower()
            
            # Wedding specific
            if "wedding" in event_type_lower:
                # Detect white (bride's dress)
                white_mask = cv2.inRange(image, (200, 200, 200), (255, 255, 255))
                white_ratio = cv2.countNonZero(white_mask) / (image.shape[0] * image.shape[1])
                
                if white_ratio > 0.15:
                    tags.append("ceremony")
                
                # Check for specific colors associated with weddings
                if is_color_present(image, (0, 0, 128), 0.1):  # Dark blue
                    tags.append("formal")
            
            # Concert/music specific
            elif "concert" in event_type_lower or "music" in event_type_lower:
                # Detect stage lighting (bright spots in dark environment)
                if "dark" in tags or "night" in tags:
                    # Find bright spots in dark setting
                    bright_spots = cv2.threshold(v_channel, 200, 255, cv2.THRESH_BINARY)[1]
                    bright_ratio = cv2.countNonZero(bright_spots) / (image.shape[0] * image.shape[1])
                    
                    if bright_ratio > 0.05 and bright_ratio < 0.3:
                        tags.append("stage_lighting")
                        tags.append("performance")
            
            # Sports specific
            elif "sports" in event_type_lower or "game" in event_type_lower:
                # Detect green field
                if green_ratio > 0.4:
                    tags.append("field")
                
                # Detect stadium features
                if "crowd" in tags and "outdoor" in tags:
                    tags.append("stadium")
            
            # Conference specific
            elif "conference" in event_type_lower or "meeting" in event_type_lower:
                # Detect presentation screens
                # Look for bright rectangular regions
                if "indoor" in tags:
                    # Simple screen detection using contours
                    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    
                    for contour in contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = float(w) / h
                        
                        # Screen-like aspect ratio and minimum size
                        if 1.2 < aspect_ratio < 2.0 and w > image.shape[1] / 5:
                            tags.append("presentation")
                            break
        
        # 3. Detection of specific compositions
        # Check for food
        if event_type and ("dinner" in event_type.lower() or "reception" in event_type.lower() or 
                           "party" in event_type.lower() or "banquet" in event_type.lower()):
            # Simple food detection based on color patterns and textures
            # This is very basic - real production would use a trained model
            saturation_mean = np.mean(s_channel)
            saturation_std = np.std(s_channel)
            
            # Food often has varied colors and textures
            if saturation_mean > 80 and saturation_std > 40 and "people" not in tags:
                tags.append("food")
                
        # 4. Quality-based tags
        # Calculate blur using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 100:
            tags.append("blurry")
        elif laplacian_var > 500:
            tags.append("sharp")
        
        # Check if it's a portrait-style photo
        if len(faces) == 1:
            face_area = faces[0][2] * faces[0][3]
            image_area = image.shape[0] * image.shape[1]
            
            if face_area / image_area > 0.15:
                tags.append("portrait")
            
        # 5. Common objects detection
        # In production, you'd use a model like YOLO or SSD
        # This is a simplified approximation
        
        # Add other contextual tags based on event type
        if event_type:
            event_lower = event_type.lower()
            
            event_tag_map = {
                'birthday': ['celebration', 'party'],
                'wedding': ['celebration', 'ceremony'],
                'corporate': ['business', 'professional'],
                'conference': ['business', 'presentation'],
                'concert': ['entertainment', 'music'],
                'festival': ['celebration', 'entertainment'],
                'sports': ['athletic', 'competition'],
                'party': ['celebration', 'social'],
                'graduation': ['academic', 'ceremony'],
                'reunion': ['social', 'gathering']
            }
            
            # Add relevant tags based on event type
            for key, value_tags in event_tag_map.items():
                if key in event_lower:
                    tags.extend(value_tags)
        
    except Exception as e:
        logger.error(f"Error in tag generation: {str(e)}", exc_info=True)
        # Add default tags if analysis fails
        if not any(tag in tags for tag in ['indoor', 'outdoor']):
            tags.append("indoor")
    
    # Return unique tags (remove duplicates)
    return list(set(tags))

def is_color_present(image, color_bgr, min_ratio=0.05):
    """Check if a specific color is present in significant amount in the image"""
    # Convert BGR color to a range
    lower_bound = np.array([max(0, c - 30) for c in color_bgr])
    upper_bound = np.array([min(255, c + 30) for c in color_bgr])
    
    # Create a mask for the color
    mask = cv2.inRange(image, lower_bound, upper_bound)
    ratio = cv2.countNonZero(mask) / (image.shape[0] * image.shape[1])
    
    return ratio > min_ratio


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

