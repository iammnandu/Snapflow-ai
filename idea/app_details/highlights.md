# highlights app documentation

## App Overview

The "highlights" app is designed to identify and manage key photos from events, specifically focusing on "best shots" and duplicate photos. It uses AI-powered tasks to automatically analyze photo quality and find similar images. The app provides views for organizers and crew members to review and curate these automatically identified highlights. The app leverages a series of tasks executed via Celery to achieve efficient photo processing.

## Models

**BestShot Model**

- Key fields:
    - `event`: Foreign key to the `Event` model.
    - `photo`: Foreign key to the `EventPhoto` model.
    - `score`: FloatField representing the quality score.
    - `category`: CharField representing the category of the best shot (e.g., 'OVERALL', 'PORTRAIT', 'BLURRY').
- Special fields/behaviors:
    - `unique_together`: Ensures a photo is only tagged once for each category in an event.
    - Categories defined for overall quality, portrait, group shot, action shot, composition, lighting, and also categories identifying problem photos (blurry, underexposed, etc.).

**DuplicateGroup Model**

- Key fields:
    - `event`: Foreign key to the `Event` model.
    - `similarity_threshold`: FloatField indicating the similarity threshold for grouping duplicate photos.
- Special fields/behaviors:
    - Groups together photos deemed similar.

**DuplicatePhoto Model**

- Key fields:
    - `group`: Foreign key to the `DuplicateGroup` model.
    - `photo`: Foreign key to the `EventPhoto` model.
    - `is_primary`: BooleanField indicating whether the photo is the primary (best) one in the group.
    - `similarity_score`: FloatField representing the similarity score to the primary photo.
- Special fields/behaviors:
    - `unique_together`: Ensures a photo is only added once to a duplicate group.

## Forms

No forms are explicitly defined in the provided code.

## Views

### Event Highlights Views

- **event_highlights**: Displays "best shots" for an event, categorized by quality metrics and identifying problem photos.
### Duplicate Photo Views

- **duplicate_photos**: Displays groups of duplicate photos for an event, allowing organizers and crew to manage duplicates.
- **duplicate_group_detail**: Displays details of a duplicate photo group, allowing organizers and crew to view and manage the photos.
- **select_primary_photo**: Sets a photo as the primary photo within a duplicate group.
- **delete_duplicate_photos**: Deletes selected photos from a duplicate group.

## Key URLs

- `/highlights/events//highlights/`: Displays event highlights (best shots).
- `/highlights/events//duplicates/`: Displays duplicate photo groups.
- `/highlights/duplicates/group//`: Displays details of a duplicate photo group.
- `/highlights/duplicates/select-primary///`: Sets a photo as the primary in a duplicate group.
- `/highlights/duplicates/group//delete-photos/`: Deletes photos from a duplicate group.

## Middleware

- **HighlightsMiddleware**: A middleware component that adds data related to highlights and duplicate photos to the context of any template where an `Event` instance is present in the context data.

## Signals

- **post_save** signal on `EventPhoto`:
    - Triggers the `process_new_photo` task to analyze the photo.
- **post_delete** signal on `EventPhoto`:
    - Triggers `update_event_best_shots` to re-calculate best shots for the event.
    - Triggers `find_duplicate_photos` to re-evaluate duplicate photos for the event.

## Analysis Functions

- **analyze_photo_advanced(photo)**: Function (assumed based on your request, not explicitly present but implied) likely responsible for orchestrating advanced photo analysis. It probably triggers quality analysis, face detection, and content tagging.

## Tasks

The app uses Celery for asynchronous task execution. Key tasks include:

- **process_photo**: Orchestrates the AI-powered photo analysis. It analyzes image quality, detects faces, and generates tags using a Celery chord for parallel execution.
    - **analyze_image_quality_task**: Analyzes the quality of an image using OpenCV metrics like sharpness, brightness and contrast to return an overall quality score.
    - **generate_tags_task**: Generates tags for an image based on its content and event type.
    - **detect_faces_optimized**: Detects faces in the image using DeepFace, extracting facial areas and associated confidence.

- **process_photo_results**: Processes and saves the results from the individual analysis tasks to the EventPhoto model. It also triggers photo enhancement if the quality score is below a certain threshold.
- **enhance_photo_task**: Creates an enhanced version of a photo using AI and saves it to the EventPhoto model.
- **detect_faces_optimized**: Detects faces in the image.
- **analyze_image_quality**: Analyzes image quality metrics and returns a score from 0-1.
- **preprocess_image**: Preprocesses images to improve face recognition accuracy.

## Integration Points

- **Events App**: The `BestShot` and `DuplicateGroup` models integrate with the `Event` model from the "events" app.
- **Photos App**: The `BestShot` and `DuplicatePhoto` models integrate with the `EventPhoto` model from the "photos" app.
- **Celery Tasks**: The app uses Celery for asynchronous tasks like photo processing, face detection, and duplicate finding.
