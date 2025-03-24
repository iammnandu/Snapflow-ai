## Privacy App

### Overview
The Privacy app provides comprehensive photo privacy management for event participants. It enables users to control their photo visibility through face blurring and photo hiding, with a workflow-driven process that requires organizer approval and advanced face recognition technology.

### Models

**PrivacyRequest Model**
- Primary fields:
  - user (Foreign Key → CustomUser)
  - event (Foreign Key → Event)
  - request_type (VARCHAR: 'blur' or 'hide')
  - status (VARCHAR: 'pending', 'approved', 'rejected', 'processing', 'completed')
  - reason (TEXT)
  - created_at (DATETIME)

- Processing fields:
  - processed_at (DATETIME)
  - processed_photos_count (INTEGER)
  - rejection_reason (TEXT)

- Constraints:
  - Unique together constraint on (user, event, request_type)

**ProcessedPhoto Model**
- Primary fields:
  - privacy_request (Foreign Key → PrivacyRequest)
  - original_photo (Foreign Key → EventPhoto)
  - processed_image (ImageField)
  - processing_date (DATETIME)
  - face_coordinates (JSON)

- Constraints:
  - Unique together constraint on (privacy_request, original_photo)

### Key URLs
- /requests/ - List participant privacy requests
- /event/<slug>/request/ - Create privacy request
- /manage/ - Organizer privacy request management
- /requests/<pk>/respond/ - Respond to privacy request

### Privacy Processing Pipeline

#### 1. Request Workflow
- User submits privacy request for event
- Organizer reviews and approves/rejects
- Approved requests trigger background processing

#### 2. Face Blurring Mechanism
- Uses face_recognition library
- Processes user's profile picture encoding
- Identifies and blurs user's faces across event photos
- Supports intensive Gaussian blur
- Tracks blurred face coordinates

#### 3. Privacy Options
- Two primary privacy actions:
  1. **Blur**: Obscures user's face in photos
     - Uses advanced face recognition
     - Generates blurred photo versions
     - Preserves photo context

  2. **Hide**: Removes photos containing user
     - Prevents photo display
     - Creates processed photo record
     - Completely removes user visibility

#### 4. Face Recognition Integration
- Extracts face encoding from user's profile picture
- Compares face encodings with photo faces
- Uses configurable matching tolerance
- Supports multiple face detection scenarios

#### 5. Background Task Processing
- Celery-powered asynchronous processing
- Handles complex image manipulation
- Manages large-scale privacy requests
- Provides detailed logging and error tracking

### Key Features
- Fine-grained photo privacy control
- Organizer-approved privacy workflow
- Advanced face detection and blurring
- Comprehensive request status tracking
- Scalable background processing