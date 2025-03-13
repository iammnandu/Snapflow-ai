
def analyze_photo_advanced(photo):
    """Advanced analysis of photo quality with detection of shot types and problems."""
    import cv2
    import numpy as np
    from PIL import Image, ImageStat
    import json

    results = {
        'quality_score': 0,
        'shot_type': None,
        'has_faces': False,
        'face_count': 0,
        'is_group_photo': False,
        'composition_score': 0,
        'lighting_score': 0,
        'technical_score': 0,
        'blur_score': 0,
        'exposure_score': 0,
        'is_underexposed': False,
        'is_overexposed': False,
        'is_accidental': False,
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
        
        # IMPROVED: Blur detection using Laplacian variance
        # Convert PIL image to OpenCV format for blur detection
        img_np = np.array(img_gray)
        laplacian = cv2.Laplacian(img_np, cv2.CV_64F)
        laplacian_var = laplacian.var()
        
        # Higher variance = less blur, normalize to 0-100
        blur_score = min((laplacian_var / 500) * 100, 100)
        
        # IMPROVED: Exposure detection
        # Calculate exposure score based on histogram distribution
        histogram = np.array(img_gray.histogram())
        
        # Check for underexposure (too many dark pixels)
        dark_ratio = np.sum(histogram[:50]) / np.sum(histogram)
        
        # Check for overexposure (too many bright pixels)
        bright_ratio = np.sum(histogram[200:]) / np.sum(histogram)
        
        # Determine exposure issues
        is_underexposed = dark_ratio > 0.5
        is_overexposed = bright_ratio > 0.5
        
        # Calculate exposure score (higher is better)
        exposure_score = 100 - (dark_ratio * 50 + bright_ratio * 50)
        
        # Check for good action shots
        is_action = False
        if hasattr(photo, 'scene_tags') and photo.scene_tags:
            try:
                tags = json.loads(photo.scene_tags)
                action_keywords = ['sport', 'action', 'running', 'jumping', 'dancing']
                if any(kw in str(tags).lower() for kw in action_keywords):
                    is_action = True
                    results['categories'].append('ACTION')
            except:
                pass
        
        # IMPROVED: Detect accidental shots (combination of blur and bad angle)
        is_accidental = blur_score < 30 and (is_underexposed or is_overexposed or composition_score < 40)
        
        # Technical score (resolution, focus, blur)
        technical_score = (
            resolution_score * 0.5 + 
            contrast_score * 0.2 + 
            blur_score * 0.3
        )
        
        # Add categories for exposure and blur issues
        if blur_score < 40:
            results['categories'].append('BLURRY')
        
        if is_underexposed:
            results['categories'].append('UNDEREXPOSED')
        
        if is_overexposed:
            results['categories'].append('OVEREXPOSED')
        
        if is_accidental:
            results['categories'].append('ACCIDENTAL')
        
        # IMPROVED: Overall quality score with better weighting
        overall_score = (
            brightness_score * 0.15 +
            contrast_score * 0.15 +
            resolution_score * 0.15 +
            composition_score * 0.15 +
            lighting_score * 0.15 +
            blur_score * 0.25  # Higher weight for blur as it's critical
        )
        
        # Heavily penalize accidental shots
        if is_accidental:
            overall_score *= 0.5
        
        # Add composition category if it's exceptionally good
        if composition_score > 85:
            results['categories'].append('COMPOSITION')
            
        # Add lighting category if it's exceptionally good
        if lighting_score > 85:
            results['categories'].append('LIGHTING')
        
        # Update all results
        results['quality_score'] = overall_score
        results['shot_type'] = shot_type
        results['has_faces'] = has_faces
        results['face_count'] = face_count
        results['is_group_photo'] = is_group_photo
        results['composition_score'] = composition_score
        results['lighting_score'] = lighting_score
        results['technical_score'] = technical_score
        results['blur_score'] = blur_score
        results['exposure_score'] = exposure_score
        results['is_underexposed'] = is_underexposed
        results['is_overexposed'] = is_overexposed
        results['is_accidental'] = is_accidental
            
    except Exception as e:
        print(f"Error in advanced analysis: {str(e)}")
        
    return results