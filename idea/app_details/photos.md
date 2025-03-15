# Photos App Documentation


## App Overview
The "photos" app is designed to manage and process event photos. It allows users to upload photos to events, view galleries, and interact with photos through likes and comments. The app also integrates AI-powered tasks for face detection, image quality analysis, and content tagging. These tasks are executed asynchronously using Celery, ensuring efficient processing without impacting the main application flow.

## Models
**EventPhoto Model**
- Key fields:
  - `event`: Foreign key to `Event` model
  - `image`: ImageField for storing photos
  - `caption`: CharField for photo captions
  - `uploaded_by`: Foreign key to the user who uploaded the photo
  - `upload_date`: DateTimeField for when the photo was uploaded
  - `processed`, `highlights`, `quality_score`, `detected_faces`, `scene_tags`, `enhanced_image`: Fields related to AI processing and enhancements
  - `view_count`, `like_count`: Engagement metrics
- Special fields/behaviors:
  - `processed`: Tracks if the photo has been processed by AI tasks
  - `delete` method: Automatically deletes associated image files when the model instance is deleted

**PhotoLike Model**
- Key fields:
  - `photo`: Foreign key to `EventPhoto`
  - `user`: Foreign key to the user who liked the photo
  - `created_at`: DateTimeField for when the like was created
- Special fields/behaviors:
  - Unique constraint on `photo` and `user` to prevent duplicate likes

**PhotoComment Model**
- Key fields:
  - `photo`: Foreign key to `EventPhoto`
  - `user`: Foreign key to the user who commented
  - `comment`: TextField for the comment content
  - `created_at`, `updated_at`: DateTimeFields for comment creation and update
- Special fields/behaviors:
  - Indexes on `photo` and `user` for efficient querying

**UserPhotoMatch Model**
- Key fields:
  - `photo`: Foreign key to `EventPhoto`
  - `user`: Foreign key to the user matched in the photo
  - `confidence_score`: FloatField for the confidence level of the match
  - `method`: CharField indicating the method used for matching
- Special fields/behaviors:
  - Unique constraint on `photo` and `user` to prevent duplicate matches

**UserGallery Model**
- Key fields:
  - `user`: OneToOneField with the user
- Special fields/behaviors:
  - `get_photos` method: Retrieves all photos where the user appears
  - `photo_count` property: Returns the number of photos in the user's gallery


## Views
### Event Gallery Views
- **EventGalleryView**: Displays a gallery of photos for an event.
- **UploadPhotosView**: Handles photo uploads for an event.
- **PhotoDetailView**: Displays details of a single photo.
- **PhotoActionView**: Handles actions related to a photo (e.g., liking, commenting).
- **DeletePhotoView**: Deletes a photo.
- **photo_comments**: Handles comments for a photo.

### User Gallery Views
- **UserGalleryView**: Displays a user's personal gallery of photos where they appear.

### Face Reanalysis View
- **reanalyze_faces**: Reanalyzes faces in a photo.

## Key URLs
- `/events//gallery/`: Displays the event gallery.
- `/events//upload/`: Uploads photos to an event.
- `/photo//`: Displays details of a photo.
- `/photo//action/`: Handles actions on a photo.
- `/photo//delete/`: Deletes a photo.
- `/photo//comments/`: Handles comments for a photo.
- `/my-gallery/`: Displays a user's personal gallery.
- `/photo//reanalyze-faces/`: Reanalyzes faces in a photo.


## Tasks
The app utilizes Celery for asynchronous task execution. Key tasks include:

- **process_photo**: Processes a photo by detecting faces, analyzing content, and enhancing quality. It uses a chord to execute tasks in parallel.
  - **analyze_image_quality_task**: Analyzes the quality of an image.
  - **generate_tags_task**: Generates tags for an image based on its content.
  - **detect_faces_optimized**: Detects faces in an image using optimized methods.
  - **process_photo_results**: Saves the results from parallel tasks to the photo model.
  - **enhance_photo_task**: Enhances the quality of a photo if its quality score is below a certain threshold.

## Integration Points
- **Events App**: The `EventPhoto` model integrates with an `Event` model from another app.
- **User App**: The `UserPhotoMatch` and `UserGallery` models integrate with the user model.
- **Celery Tasks**: The app uses Celery for asynchronous tasks like photo processing and face detection.

