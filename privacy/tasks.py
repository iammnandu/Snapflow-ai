# privacy/tasks.py
import os
import cv2
import numpy as np
import logging
import tempfile
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from celery import shared_task

from photos.models import EventPhoto
from users.models import CustomUser
from .models import PrivacyRequest, ProcessedPhoto

logger = logging.getLogger(__name__)

@shared_task
def process_privacy_request(request_id):
    """Process a privacy request after it's been approved."""
    try:
        # First fetch the privacy request
        privacy_request = PrivacyRequest.objects.get(id=request_id)
        
        with transaction.atomic():
            # Lock the row for update
            privacy_request = PrivacyRequest.objects.select_for_update().get(id=request_id)
            
            # Check if the request is in the correct state
            if privacy_request.status != 'approved':
                logger.warning(f"Privacy request {request_id} is not in 'approved' state: {privacy_request.status}")
                return False
            
            # Update status to processing
            privacy_request.status = 'processing'
            privacy_request.save()
        
        # Get all photos from the event
        event_photos = EventPhoto.objects.filter(event=privacy_request.event)
        logger.info(f"Processing {len(event_photos)} photos for privacy request {request_id}")
        
        # Get user face encoding if needed
        user = privacy_request.user
        if privacy_request.request_type in ['blur', 'hide']:
            user_encoding = get_user_face_encoding(user)
            # Check if encoding exists
            if user_encoding is None:
                logger.error(f"Failed to get face encoding for user {user.id}. User may not have a valid avatar.")
                with transaction.atomic():
                    privacy_request = PrivacyRequest.objects.select_for_update().get(id=request_id)
                    privacy_request.status = 'rejected'
                    privacy_request.rejection_reason = "Could not process your face from your profile picture. Please upload a clear profile photo with your face visible."
                    privacy_request.save()
                return False
        
        # Process different request types
        if privacy_request.request_type == 'blur':
            process_blur_request(privacy_request, event_photos)
        elif privacy_request.request_type == 'hide':
            process_hide_request(privacy_request, event_photos)
        
        # Update request status after completion
        with transaction.atomic():
            privacy_request = PrivacyRequest.objects.select_for_update().get(id=request_id)
            privacy_request.status = 'completed'
            privacy_request.processed_at = timezone.now()
            privacy_request.processed_photos_count = privacy_request.processed_photos.count()
            privacy_request.save()
        
        logger.info(f"Completed processing privacy request {request_id}")
        return True
    
    except Exception as e:
        import traceback
        logger.error(f"Error processing privacy request {request_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Update status to error
        try:
            # First need to get the privacy_request object if it doesn't exist in this scope
            privacy_request = PrivacyRequest.objects.get(id=request_id)
            with transaction.atomic():
                privacy_request = PrivacyRequest.objects.select_for_update().get(id=request_id)
                privacy_request.status = 'error'
                privacy_request.rejection_reason = f"Processing error: {str(e)}"
                privacy_request.save()
        except Exception as update_error:
            logger.error(f"Failed to update privacy request status: {str(update_error)}")
        
        return False


def process_blur_request(privacy_request, event_photos):
    """Process a request to blur a user's face in photos."""
    import shutil
    
    user = privacy_request.user
    processed_count = 0
    
    # Get user face encodings (assuming a profile picture exists)
    user_encoding = get_user_face_encoding(user)
    if user_encoding is None:
        logger.error(f"No face encoding available for user {user.id}")
        return
    
    # Process each photo
    for photo in event_photos:
        try:
            # Check if user is in this photo
            if not user_is_in_photo(photo, user):
                continue
            
            # Check if there's already a blurred version of this photo
            existing_processed = ProcessedPhoto.objects.filter(
                original_photo=photo,
                privacy_request__request_type='blur',
                privacy_request__status='completed',
                processed_image__isnull=False
            ).first()
            
            if existing_processed:
                # Use the existing blurred image as starting point
                logger.info(f"Using existing blurred version for photo {photo.id}")
                image_path = os.path.join(settings.MEDIA_ROOT, str(existing_processed.processed_image))
                if not os.path.exists(image_path):
                    logger.warning(f"Existing blurred image doesn't exist: {image_path}")
                    image_path = photo.image.path
            else:
                # Use original image
                image_path = photo.image.path
            
            if not os.path.exists(image_path):
                logger.warning(f"Image doesn't exist: {image_path}")
                continue
            
            # Process the image
            processed_image, face_locations = blur_user_face(image_path, user_encoding, blur_factor=101)  # Increased blur factor
            if processed_image is None:
                continue
            
            # Save the processed image
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_path = temp_file.name
                cv2.imwrite(temp_path, processed_image)
            
            # Create processed photo record
            processed_photo = ProcessedPhoto(
                privacy_request=privacy_request,
                original_photo=photo,
                face_coordinates=face_locations
            )
            
            # Save the processed image to media
            filename = f"privacy_{photo.id}_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
            relative_path = os.path.join('privacy_processed', filename)
            final_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Use shutil.copy2 instead of os.rename to handle cross-drive operations
            shutil.copy2(temp_path, final_path)
            # Delete the temp file after copying
            os.unlink(temp_path)
            
            processed_photo.processed_image = relative_path
            processed_photo.save()
            
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing photo {photo.id}: {str(e)}")
    
    logger.info(f"Processed {processed_count} photos for blur request {privacy_request.id}")
    return processed_count



def process_hide_request(privacy_request, event_photos):
    """Process a request to hide photos containing a user."""
    user = privacy_request.user
    processed_count = 0
    
    # Get user face encoding
    user_encoding = get_user_face_encoding(user)
    if user_encoding is None:
        logger.error(f"No face encoding available for user {user.id}")
        return
    
    # Process each photo
    for photo in event_photos:
        try:
            # Check if user is in this photo
            if user_is_in_photo(photo, user):
                # Create a processed photo record (with no image) to mark it as hidden
                # Make sure it doesn't already exist
                existing_record = ProcessedPhoto.objects.filter(
                    privacy_request=privacy_request,
                    original_photo=photo
                ).first()
                
                if not existing_record:
                    ProcessedPhoto.objects.create(
                        privacy_request=privacy_request,
                        original_photo=photo
                    )
                    processed_count += 1
        except Exception as e:
            logger.error(f"Error processing hide request for photo {photo.id}: {str(e)}")
    
    logger.info(f"Hidden {processed_count} photos for hide request {privacy_request.id}")
    return processed_count


def user_is_in_photo(photo, user):
    """Check if a user appears in a photo using existing matches."""
    from photos.models import UserPhotoMatch
    
    # Check if there's an existing match record
    match = UserPhotoMatch.objects.filter(photo=photo, user=user).first()
    return match is not None


def get_user_face_encoding(user):
    """Get face encoding for a user from their profile picture."""
    import face_recognition
    
    # Check if user has a profile picture
    if not user.avatar:
        return None
    
    # Load the user's avatar image
    avatar_path = os.path.join(settings.MEDIA_ROOT, str(user.avatar))
    if not os.path.exists(avatar_path):
        return None
    
    try:
        # Load image with face_recognition
        image = face_recognition.load_image_file(avatar_path)
        
        # Find faces in the image
        face_locations = face_recognition.face_locations(image)
        if not face_locations:
            return None
        
        # Generate encodings for the face
        face_encodings = face_recognition.face_encodings(image, face_locations)
        if not face_encodings:
            return None
        
        # Return the first encoding
        return face_encodings[0]
    
    except Exception as e:
        logger.error(f"Error getting face encoding for user {user.id}: {str(e)}")
        return None

def blur_user_face(image_path, user_encoding, blur_factor=101):  # Increased from 51 to 101
    """
    Blur the face of a specific user in an image.
    
    Args:
        image_path: Path to the image file
        user_encoding: Face encoding of the user to blur
        blur_factor: Blur intensity (must be odd number)
        
    Returns:
        processed_image: The image with blurred face
        face_locations: List of coordinates of blurred faces
    """
    import face_recognition
    
    try:
        # Ensure blur factor is odd
        if blur_factor % 2 == 0:
            blur_factor += 1
        
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to load image: {image_path}")
            return None, None
        
        # Convert BGR to RGB (face_recognition uses RGB)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Find all faces in the image
        face_locations = face_recognition.face_locations(rgb_image)
        if not face_locations:
            return image, []
        
        # Get encodings for all faces
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        # Track which faces match the user
        blurred_faces = []
        
        # Check each face for a match with the user
        for i, face_encoding in enumerate(face_encodings):
            # Compare with user encoding
            matches = face_recognition.compare_faces([user_encoding], face_encoding, tolerance=0.6)
          
            # Use .any() for NumPy array boolean evaluation
            if matches[0].any():
                # This face matches the user - blur it
                top, right, bottom, left = face_locations[i]
                
                # Extract the face region
                face_region = image[top:bottom, left:right]
                
                # Apply intensive Gaussian blur
                blurred_face = cv2.GaussianBlur(face_region, (blur_factor, blur_factor), 0)
                
                # Replace the face region with the blurred version
                image[top:bottom, left:right] = blurred_face
                
                # Add to list of blurred faces
                blurred_faces.append({
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "left": left
                })
        
        # Return the processed image and face locations
        return image, blurred_faces
    
    except Exception as e:
        logger.error(f"Error blurring face in image {image_path}: {str(e)}")
        return None, None


def check_photo_privacy(photo, user=None):
    """
    Check if a photo should be hidden or has privacy-processed versions.
    
    This function can be called from templates to determine how to display photos.
    
    Args:
        photo: An EventPhoto instance
        user: The user viewing the photo (optional)
        
    Returns:
        dict: Privacy status information for the photo
    """
    result = {
        'is_hidden': False,
        'has_blurred_version': False,
        'blurred_image': None
    }
    
    # Check if the photo is hidden due to any hide requests
    hide_requests = ProcessedPhoto.objects.filter(
        original_photo=photo,
        privacy_request__request_type='hide',
        privacy_request__status='completed',
        processed_image__isnull=True  # For hide requests, no processed image is stored
    ).exists()
    
    if hide_requests:
        result['is_hidden'] = True
    
    # Check if there's a blurred version of this photo
    blurred_version = ProcessedPhoto.objects.filter(
        original_photo=photo,
        privacy_request__request_type='blur',
        privacy_request__status='completed',
        processed_image__isnull=False
    ).first()
    
    if blurred_version:
        result['has_blurred_version'] = True
        result['blurred_image'] = blurred_version.processed_image
    
    return result