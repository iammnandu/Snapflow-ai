# SnapFlow: Event Photo Management Web Application

Based on the provided documentation, SnapFlow is a comprehensive Django-based web application designed for event photo management with advanced face recognition capabilities. The system intelligently categorizes photos by participants and provides personalized galleries.

## Core Structure

The application consists of three main Django apps:

1. **Users** - Handles authentication and user management
2. **Events** - Manages event creation and configuration
3. **Photos** - Processes and organizes photos with AI capabilities

Let's explore each module in detail:

## 1. Users App

### Overview
The Users app manages authentication and supports three distinct user types with specialized capabilities.

### User Types
- **Event Organizer**: Creates and manages events, crews, participants
- **Photographer**: Captures and uploads event photos
- **Participant**: Views photos where they've been identified

### Models

**CustomUser Model**
- Primary fields:
  - id (INT, Primary Key)
  - username (VARCHAR(150), Unique)
  - email (VARCHAR(254), Unique)
  - password (VARCHAR(128))
  - first_name, last_name (VARCHAR(150))
  - date_joined, last_login (DATETIME)
  - is_active, is_staff, is_superuser (BOOLEAN)
  - role (VARCHAR(20), Choices: ORGANIZER, PHOTOGRAPHER, PARTICIPANT)
  
- Common fields:
  - avatar (VARCHAR(255), Image Path)
  - phone_number (VARCHAR(15))
  
- Role-specific fields:
  - Organizer: company_name, website
  - Photographer: portfolio_url, photographer_role, watermark
  - Participant: participant_type, image_visibility, blur_requested, remove_requested, is_verified

### Key URLs
- /register/ - User registration
- /profile/ - View profile
- /profile/update/ - Update profile
- /complete-profile/ - Complete profile after initial registration
- /dashboard/ - User dashboard
- /privacy/update/ - Update privacy settings
- /delete-account/ - Account deletion

### Forms
- **UserTypeSelectionForm**: Selects user type during registration
- **BasicRegistrationForm**: Basic fields for initial registration
- **OrganizerProfileForm**: Company details for organizers
- **PhotographerProfileForm**: Portfolio and equipment info for photographers
- **ParticipantProfileForm**: Privacy preferences for participants

## 2. Events App

### Overview
This app manages all event-related functionality, including creation, configuration, and management of participants and crews.

### Models

**Event Model**
- Primary fields:
  - id (INT, Primary Key)
  - title, slug (VARCHAR(255))
  - event_type (VARCHAR(50))
  - description (TEXT)
  - start_date, end_date (DATETIME)
  - timezone (VARCHAR(50))
  - location (VARCHAR(255))
  - event_code (VARCHAR(50), Unique)
  - primary_color, secondary_color (VARCHAR(7))
  - status (VARCHAR(50))
  - organizer (Foreign Key → CustomUser)
  
- Feature flags:
  - is_public, require_registration, allow_guest_upload
  - enable_face_detection, enable_moment_detection, enable_auto_tagging
  
- Media fields:
  - logo, cover_image (VARCHAR(255))
  - custom_domain (VARCHAR(255))
  - theme (Foreign Key → EventTheme)

**EventTheme Model**
- id, name, description, template
- thumbnail, primary_color, secondary_color, font_family
- is_active, created_at, updated_at

**EventCrew Model**
- event (Foreign Key → Event)
- member (Foreign Key → CustomUser)
- role, is_confirmed, notes, equipment, assigned_area
- created_at, updated_at

**EventParticipant Model**
- event (Foreign Key → Event)
- user (Foreign Key → CustomUser, Optional)
- email, name, participant_type
- is_registered, registration_code
- allow_photos, request_blur
- created_at, updated_at

**EventConfiguration Model**
- event (Foreign Key → Event)
- Feature toggles: enable_comments, enable_likes, enable_download, download_watermark
- Configuration: max_upload_size, allowed_formats
- AI features: enable_face_grouping, enable_scene_detection, enable_quality_filter
- Notifications: notify_on_upload, notify_on_comment

**EventAccessRequest Model**
- event (Foreign Key → Event)
- user (Foreign Key → CustomUser)
- request_type, status, message
- created_at, updated_at

### Key URLs
- /create/ - Create new event
- /<slug>/dashboard/ - Event dashboard
- /<slug>/edit/ - Edit event details
- /<slug>/setup/<step>/ - Setup wizard
- /<slug>/crew/ - Manage photographers
- /<slug>/participants/ - Manage participants
- /<slug>/equipment/ - Configure equipment settings
- /access/request/ - Request event access

### Forms
- **EventCreationForm**: Creates new events
- **EventConfigurationForm**: Configures event settings
- **CrewInvitationForm**: Invites photographers
- **ParticipantInvitationForm**: Invites participants
- **EventThemeForm**: Customizes event appearance
- **PrivacySettingsForm**: Sets privacy parameters
- **EventAccessRequestForm**: Requests event access

## 3. Photos App

### Overview
The Photos app handles the core functionality of photo processing, including AI-powered face recognition, quality analysis, and auto-tagging.

### Models

**EventPhoto Model**
- id (INT, Primary Key)
- event (Foreign Key → Event)
- image (VARCHAR(255))
- caption (VARCHAR(200))
- uploaded_by (Foreign Key → CustomUser)
- upload_date (DATETIME)
- processed (BOOLEAN)
- quality_score (FLOAT)
- detected_faces (JSON)
- scene_tags (JSON)
- enhanced_image (VARCHAR(255))
- view_count, like_count (INT)

**PhotoLike Model**
- photo (Foreign Key → EventPhoto)
- user (Foreign Key → CustomUser)
- created_at (DATETIME)

**PhotoComment Model**
- photo (Foreign Key → EventPhoto)
- user (Foreign Key → CustomUser)
- comment (TEXT)
- created_at, updated_at (DATETIME)

**UserPhotoMatch Model**
- photo (Foreign Key → EventPhoto)
- user (Foreign Key → CustomUser)
- confidence_score (FLOAT)
- method (VARCHAR(100))
- created_at (DATETIME)

**UserGallery Model**
- user (One-to-One Foreign Key → CustomUser)
- created_at (DATETIME)

### Key URLs
- /<slug>/gallery/ - Event gallery view
- /<slug>/upload/ - Upload photos
- /photo/<pk>/ - Photo detail view
- /photo/<pk>/action/ - Like/unlike photos
- /photo/<pk>/comments/ - View/add comments
- /my-gallery/ - Personalized user gallery
- /photo/<pk>/reanalyze-faces/ - Reprocess face detection

### Photo Processing Pipeline

#### 1. Main Processing Flow
- **process_photo(photo_id)**: Entry point for processing
  - Retrieves photo from database
  - Checks processing status
  - Loads image with OpenCV
  - Sets up parallel processing tasks
  - Returns combined results

- **process_photo_results(results, photo_id)**: Callback function
  - Collects results from parallel tasks
  - Updates EventPhoto with data
  - Triggers enhancement for low-quality photos

#### 2. Face Detection & Recognition
- Multiple algorithms working together:
  - Uses RetinaFace for detection
  - Extracts and aligns faces using landmarks
  - Generates face representations with multiple models
  - Matches faces to users with confidence scoring

- Face recognition models:
  - face_recognition library (dlib wrapper)
  - DeepFace models (Facenet, VGG-Face, ArcFace)

- Optimizations:
  - User encoding caching
  - Parallel processing
  - Face alignment
  - Image preprocessing

#### 3. Image Quality Analysis
- Evaluates photos using three metrics:
  - Sharpness (Laplacian variance)
  - Brightness (average pixel value)
  - Contrast (standard deviation)
  - Combined weighted score between 0-1

#### 4. Image Enhancement
- Triggers for quality scores below 0.7
- Applies three enhancements:
  - 20% contrast increase
  - 10% brightness boost
  - 50% sharpening
  - Saves enhanced version

#### 5. Tagging System
- Analyzes HSV color profile
- Detects outdoor scenes
- Evaluates lighting conditions
- Incorporates event type

## Libraries & Technologies

1. **Web Framework**
   - Django - Web application framework

2. **Computer Vision & AI**
   - OpenCV (cv2) - Image processing
   - face_recognition - High-level face recognition
   - DeepFace - Deep learning models
   - PIL - Image enhancement
   - numpy - Numerical processing

3. **Asynchronous Processing**
   - Celery - Distributed task queue
   - ThreadPoolExecutor - Parallel processing

4. **Data Processing**
   - numpy - Array operations
   - scipy - Distance calculations

The entire system is designed to efficiently process large numbers of event photos while providing intelligent face recognition and personalized galleries for participants, significantly enhancing the event photography experience for all users.