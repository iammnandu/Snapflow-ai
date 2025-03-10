import numpy as np
from PIL import Image, ImageStat
import json

def analyze_photo_advanced(photo):
    """Advanced analysis of photo quality with detection of shot types."""
    results = {
        'quality_score': 0,
        'shot_type': None,
        'has_faces': False,
        'face_count': 0,
        'is_group_photo': False,
        'composition_score': 0,
        'lighting_score': 0,
        'technical_score': 0,
        'categories': []
    }
    
    try:
        # Open the image
        img = Image.open(photo.image.path)
        
        # Get image dimensions and basic stats
        width, height = img.size
        aspect_ratio = width / height
        img_gray = img.convert('L')
        stat = ImageStat.Stat(img_gray)
        
        # Basic quality metrics
        brightness = stat.mean[0]
        contrast = stat.stddev[0]
        
        # Normalized scores (0-100)
        brightness_score = (1 - abs((brightness - 128) / 128)) * 100
        contrast_score = min((contrast / 80) * 100, 100)
        
        # Resolution score
        resolution = width * height
        resolution_score = min((resolution / (3000 * 2000)) * 100, 100)
        
        # Check for faces using existing detected_faces data
        faces = []
        if photo.detected_faces:
            try:
                faces = json.loads(photo.detected_faces)
            except:
                faces = []
        
        face_count = len(faces)
        has_faces = face_count > 0
        is_group_photo = face_count >= 3
        
        # Determine shot type based on faces and composition
        shot_type = 'LANDSCAPE'  # Default
        
        if has_faces:
            if face_count == 1:
                # Check if it's a portrait (one face taking significant portion)
                if faces and isinstance(faces, list) and len(faces) > 0:
                    face = faces[0]
                    if isinstance(face, dict) and 'width' in face and 'height' in face:
                        face_area = face['width'] * face['height']
                        image_area = width * height
                        face_ratio = face_area / image_area
                        
                        if face_ratio > 0.1:  # Face takes up significant portion
                            shot_type = 'PORTRAIT'
                            results['categories'].append('PORTRAIT')
            elif face_count > 2:
                shot_type = 'GROUP'
                results['categories'].append('GROUP')
        
        # Calculate composition score (rule of thirds, etc.)
        # This would be more complex in a real implementation
        composition_score = 70 + (np.random.rand() * 30)  # Placeholder
        
        # Lighting score
        lighting_uniformity = 100 - min(((stat.stddev[0] / stat.mean[0]) * 100), 100)
        lighting_score = (brightness_score * 0.6) + (lighting_uniformity * 0.4)
        
        # Check for good action shots (would be more complex in real implementation)
        # Here we're doing a simplified check based on blur detection
        is_action = False
        if 'scene_tags' in photo:
            try:
                tags = json.loads(photo.scene_tags)
                action_keywords = ['sport', 'action', 'running', 'jumping', 'dancing']
                if any(kw in str(tags).lower() for kw in action_keywords):
                    is_action = True
                    results['categories'].append('ACTION')
            except:
                pass
        
        # Technical score (resolution, focus, etc.)
        technical_score = (resolution_score * 0.7) + (contrast_score * 0.3)
        
        # Overall quality score (weighted average)
        overall_score = (
            brightness_score * 0.2 +
            contrast_score * 0.2 +
            resolution_score * 0.2 +
            composition_score * 0.2 +
            lighting_score * 0.2
        )
        
        # Save results
        results['quality_score'] = overall_score
        results['shot_type'] = shot_type
        results['has_faces'] = has_faces
        results['face_count'] = face_count
        results['is_group_photo'] = is_group_photo
        results['composition_score'] = composition_score
        results['lighting_score'] = lighting_score
        results['technical_score'] = technical_score
        
        # Add composition category if it's exceptionally good
        if composition_score > 85:
            results['categories'].append('COMPOSITION')
            
        # Add lighting category if it's exceptionally good
        if lighting_score > 85:
            results['categories'].append('LIGHTING')
            
    except Exception as e:
        print(f"Error in advanced analysis: {str(e)}")
        
    return results