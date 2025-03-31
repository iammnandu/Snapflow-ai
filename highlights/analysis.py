# highlights/analysis.py
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
        
        # IMPROVED: Blur detection using combination of Laplacian variance and face-aware analysis
        # Convert PIL image to OpenCV format for blur detection
        img_np = np.array(img_gray)
        laplacian = cv2.Laplacian(img_np, cv2.CV_64F)
        laplacian_var = laplacian.var()
        
        # Higher variance = less blur, normalize to 0-100
        raw_blur_score = min((laplacian_var / 500) * 100, 100)
        
        # Add face-aware blur detection
        is_portrait = shot_type == 'PORTRAIT'
        is_group = shot_type == 'GROUP'
        
        # Adjust blur thresholds based on image type
        if is_portrait:
            # Portraits often have background blur (bokeh effect)
            # Only consider a portrait blurry if it's severely blurred
            if laplacian_var < 80:
                blur_score = max(raw_blur_score * 0.7, 10)  # Severely blurry portrait
            elif laplacian_var < 150:
                blur_score = max(raw_blur_score * 0.9, 40)  # Moderately blurry portrait
            else:
                # Increase score for portraits with acceptable sharpness
                blur_score = min(raw_blur_score * 1.2, 100)
                
            # Check if faces are present and analyze face regions for blur
            if faces and isinstance(faces, list) and len(faces) > 0:
                face_sharpness_scores = []
                for face in faces:
                    if isinstance(face, dict) and 'x' in face and 'y' in face and 'width' in face and 'height' in face:
                        # Extract face region and compute its Laplacian variance
                        face_x, face_y = int(face['x']), int(face['y'])
                        face_w, face_h = int(face['width']), int(face['height'])
                        
                        # Ensure coordinates are within image bounds
                        face_x = max(0, face_x)
                        face_y = max(0, face_y)
                        face_w = min(width - face_x, face_w)
                        face_h = min(height - face_y, face_h)
                        
                        if face_w > 0 and face_h > 0:
                            face_region = img_np[face_y:face_y+face_h, face_x:face_x+face_w]
                            if face_region.size > 0:
                                face_laplacian = cv2.Laplacian(face_region, cv2.CV_64F)
                                face_var = face_laplacian.var()
                                face_sharpness_scores.append(face_var)
                
                # If we have face sharpness scores, prioritize them over whole image
                if face_sharpness_scores:
                    avg_face_var = sum(face_sharpness_scores) / len(face_sharpness_scores)
                    face_blur_score = min((avg_face_var / 300) * 100, 100)
                    
                    # Weighted average: 70% face sharpness, 30% overall sharpness
                    blur_score = (face_blur_score * 0.7) + (blur_score * 0.3)
        elif is_group:
            # Group shots need good overall sharpness but might have some bokeh
            if laplacian_var < 100:
                blur_score = max(raw_blur_score * 0.8, 20)  # Severely blurry group
            elif laplacian_var < 200:
                blur_score = max(raw_blur_score * 0.9, 40)  # Moderately blurry group
            else:
                blur_score = raw_blur_score
        else:
            # Non-portrait shots (landscapes, etc.) - use stricter thresholds
            if laplacian_var < 100:
                blur_score = max(raw_blur_score * 0.7, 10)  # Severely blurry
            elif laplacian_var < 300:
                blur_score = max(raw_blur_score * 0.9, 30)  # Moderately blurry
            else:
                blur_score = raw_blur_score
        
        # IMPROVED: Exposure detection
        # Calculate exposure score based on histogram distribution
        histogram = np.array(img_gray.histogram())
        total_pixels = np.sum(histogram)
        
        # Check for underexposure (too many dark pixels)
        dark_ratio = np.sum(histogram[:50]) / total_pixels
        
        # Check for overexposure (too many bright pixels)
        bright_ratio = np.sum(histogram[200:]) / total_pixels
        
        # More precise exposure score calculation
        mid_range_ratio = np.sum(histogram[50:200]) / total_pixels
        exposure_score = mid_range_ratio * 100  # Higher ratio in middle range = better exposure
        
        # Determine exposure issues with more accurate thresholds
        is_underexposed = dark_ratio > 0.5 or brightness < 60
        is_overexposed = bright_ratio > 0.5 or brightness > 200
        
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
        
        # IMPROVED: Detect accidental shots with more accurate criteria
        technical_issues = 0
        
        # For blur, use different thresholds based on shot type
        if is_portrait:
            if blur_score < 30:  # More permissive for portraits
                technical_issues += 1
        elif is_group:
            if blur_score < 35:  # Slightly more permissive for groups
                technical_issues += 1
        else:
            if blur_score < 40:  # Standard threshold for other shots
                technical_issues += 1
                
        if is_underexposed or is_overexposed:
            technical_issues += 1
        if composition_score < 40:
            technical_issues += 1
            
        # An image with 2 or more significant technical issues is likely accidental
        is_accidental = technical_issues >= 2
        
        # Technical score (resolution, focus, blur)
        technical_score = (
            resolution_score * 0.4 + 
            contrast_score * 0.2 + 
            blur_score * 0.4
        )
        
        # Add categories for exposure and blur issues, with shot-type awareness
        if is_portrait:
            # More permissive blur threshold for portraits
            if blur_score < 30:
                results['categories'].append('BLURRY')
        elif is_group:
            # Slightly more permissive blur threshold for group shots
            if blur_score < 35:
                results['categories'].append('BLURRY')
        else:
            # Standard blur threshold for other shots
            if blur_score < 40:
                results['categories'].append('BLURRY')
        
        if is_underexposed:
            results['categories'].append('UNDEREXPOSED')
        
        if is_overexposed:
            results['categories'].append('OVEREXPOSED')
        
        if is_accidental:
            results['categories'].append('ACCIDENTAL')
        
        # IMPROVED: Overall quality score with better weighting and penalties
        # Different calculation paths based on image problems
        if blur_score < 40:
            # Penalize blurry photos, but less severely for portraits with intentional bokeh
            penalty_factor = 0.8 if is_portrait else 0.7  # 20% penalty for portraits, 30% for others
            
            overall_score = max(
                (brightness_score * 0.10 +
                contrast_score * 0.10 +
                resolution_score * 0.10 +
                composition_score * 0.10 +
                lighting_score * 0.10 +
                blur_score * 0.50) * penalty_factor,
                10  # Minimum score floor
            )
        elif is_underexposed or is_overexposed:
            # Penalize exposure problems
            overall_score = max(
                (brightness_score * 0.10 +
                contrast_score * 0.10 +
                resolution_score * 0.15 +
                composition_score * 0.15 +
                lighting_score * 0.10 +
                blur_score * 0.20 +
                exposure_score * 0.20) * 0.8,  # 20% penalty
                20  # Minimum score floor
            )
        else:
            # Normal weighting for good photos
            overall_score = (
                brightness_score * 0.15 +
                contrast_score * 0.15 +
                resolution_score * 0.15 +
                composition_score * 0.20 +
                lighting_score * 0.15 +
                blur_score * 0.20
            )
        
        # Heavily penalize accidental shots
        if is_accidental:
            overall_score = max(overall_score * 0.5, 5)  # 50% penalty, minimum 5
        
        # Add composition category if it's exceptionally good
        if composition_score > 85 and blur_score >= 60 and not is_underexposed and not is_overexposed:
            results['categories'].append('COMPOSITION')
            
        # Add lighting category if it's exceptionally good
        if lighting_score > 85 and blur_score >= 60 and not is_underexposed and not is_overexposed:
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