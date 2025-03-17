# SnapFlow: Event Photo Management Web Application

SnapFlow is a comprehensive Django-based web application designed for event photo management with advanced face recognition capabilities. The system intelligently categorizes photos by participants and provides personalized galleries.

## Core Structure

The application consists of three main Django apps:

1. **Users** - Handles authentication and user management
2. **Events** - Manages event creation and configuration
3. **Photos** - Processes and organizes photos with AI capabilities
4. **Notifications** - sent notifications to users through email or in app notifications
5. **Highlights** - Find the best shots and categorize photos from the events.
6. **Privacy** - handles the privacy for photos and events with users.


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
The Photos app forms the core photo management system in SnapFlow. It handles photo uploads, processing, face recognition, and user engagement features like comments and likes. The app enables intelligent organization of photos and provides personalized galleries for participants.

### Models

**EventPhoto Model**
- Primary fields:
  - event (Foreign Key → Event)
  - image (ImageField)
  - caption (VARCHAR(200))
  - uploaded_by (Foreign Key → CustomUser)
  - upload_date (DATETIME)

- AI Processing fields:
  - processed (BOOLEAN)
  - highlights (BOOLEAN)
  - quality_score (FLOAT)
  - detected_faces (JSON)
  - scene_tags (JSON)
  - enhanced_image (ImageField)

- Engagement metrics:
  - view_count (INTEGER)
  - like_count (INTEGER)

- File management features:
  - Custom upload path generation
  - Automatic file cleanup on deletion

**PhotoLike Model**
- Primary fields:
  - photo (Foreign Key → EventPhoto)
  - user (Foreign Key → CustomUser)
  - created_at (DATETIME)
- Constraints:
  - Unique together constraint on (photo, user)

**PhotoComment Model**
- Primary fields:
  - photo (Foreign Key → EventPhoto)
  - user (Foreign Key → CustomUser)
  - comment (TEXT)
  - created_at (DATETIME)
  - updated_at (DATETIME)

**UserPhotoMatch Model**
- Primary fields:
  - photo (Foreign Key → EventPhoto)
  - user (Foreign Key → CustomUser)
  - confidence_score (FLOAT)
  - created_at (DATETIME)
  - method (VARCHAR(100))
- Constraints:
  - Unique together constraint on (photo, user)

**UserGallery Model**
- Primary fields:
  - user (OneToOneField → CustomUser)
  - created_at (DATETIME)
- Methods:
  - get_photos: Retrieves all photos where user appears
  - photo_count: Property that counts user's photos

### Key URLs
- /<slug>/gallery/ - View event gallery
- /<slug>/upload/ - Upload photos to event
- /photo/<pk>/ - View photo details
- /photo/<pk>/action/ - Perform actions on photos
- /photo/<pk>/delete/ - Delete photo
- /photo/<pk>/comments/ - View and add comments
- /my-gallery/ - View personal gallery
- /photo/<pk>/reanalyze-faces/ - Re-process face detection


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



## 4. Notifications App

### Overview
The Notifications app manages the system-wide notification infrastructure, handling both in-app and email notifications. It provides flexible user preference configuration and supports various notification types across the platform, ensuring users stay informed about relevant activities.

### Models

**NotificationPreference Model**
- Primary fields:
  - user (OneToOneField → CustomUser)
  - created_at, updated_at (DATETIME)
  
- Email notification toggles:
  - email_event_invites (BOOLEAN)
  - email_photo_tags (BOOLEAN)
  - email_comments (BOOLEAN)
  - email_likes (BOOLEAN)
  - email_new_photos (BOOLEAN)
  - email_event_updates (BOOLEAN)
  - email_crew_assignments (BOOLEAN)
  
- In-app notification toggles:
  - app_event_invites (BOOLEAN)
  - app_photo_tags (BOOLEAN)
  - app_comments (BOOLEAN)
  - app_likes (BOOLEAN)
  - app_new_photos (BOOLEAN)
  - app_event_updates (BOOLEAN)
  - app_crew_assignments (BOOLEAN)
  
- Digest options:
  - receive_daily_digest (BOOLEAN)
  - receive_weekly_digest (BOOLEAN)

**Notification Model**
- Primary fields:
  - recipient (Foreign Key → CustomUser)
  - from_user (Foreign Key → CustomUser, Optional)
  - notification_type (VARCHAR(30), Choices: event_invite, photo_tag, comment, etc.)
  - title (VARCHAR(255))
  - message (TEXT)
  - created_at, updated_at (DATETIME)
  
- Content reference fields:
  - content_type (Foreign Key → ContentType)
  - object_id (INTEGER)
  - content_object (GenericForeignKey)
  - action_url (VARCHAR(255))
  
- Status fields:
  - is_read (BOOLEAN)
  - is_email_sent (BOOLEAN)
  
- Methods:
  - get_icon_class: Returns appropriate icon based on notification type
  - get_absolute_url: Generates target URL for notification content

**EmailLog Model**
- Primary fields:
  - notification (Foreign Key → Notification)
  - recipient_email (EMAIL)
  - subject (VARCHAR(255))
  - body (TEXT)
  - sent_at (DATETIME)
  - status (VARCHAR(20))
  - error_message (TEXT)

### Key URLs
- / - List all notifications
- /<notification_id>/ - View notification details
- /<notification_id>/mark-read/ - Mark notification as read
- /<notification_id>/delete/ - Delete notification
- /mark-all-read/ - Mark all notifications as read
- /preferences/ - Manage notification preferences

### Forms
- **NotificationPreferenceForm**: Configures user notification settings
  - Email notification toggles with checkbox widgets
  - In-app notification toggles with checkbox widgets
  - Digest options with help text
  - Organized into three field categories: email, app, and digest settings
  - Customized labels for better user understanding


## 5. Highlights App

### Overview
The Highlights app provides advanced photo curation features for events, including best shot selection and duplicate photo management. It helps organizers and photographers identify high-quality images and remove redundant photos, streamlining the event photo collection.

### Models

**BestShot Model**
- Primary fields:
  - event (Foreign Key → Event)
  - photo (Foreign Key → EventPhoto)
  - score (FLOAT)
  - category (VARCHAR(50), Choices: OVERALL, PORTRAIT, GROUP, ACTION, etc.)
  - created_at, updated_at (DATETIME)
  
- Positive categories:
  - Overall Quality
  - Best Portrait
  - Best Group Shot
  - Best Action Shot
  - Best Composition
  - Best Lighting
  
- Problem categories:
  - Blurry Images
  - Underexposed Images
  - Overexposed Images
  - Accidental Shots
  
- Constraints:
  - Unique together constraint on (event, category, photo)
  - Ordering by score (descending)

**DuplicateGroup Model**
- Primary fields:
  - event (Foreign Key → Event)
  - similarity_threshold (FLOAT)
  - created_at, updated_at (DATETIME)

**DuplicatePhoto Model**
- Primary fields:
  - group (Foreign Key → DuplicateGroup)
  - photo (Foreign Key → EventPhoto)
  - is_primary (BOOLEAN)
  - similarity_score (FLOAT)
  
- Constraints:
  - Unique together constraint on (group, photo)
  - Ordering by is_primary (descending), similarity_score (descending)

### Key URLs
- /events/<slug>/highlights/ - View event highlights
- /events/<slug>/duplicates/ - View duplicate photos
- /duplicates/group/<id>/ - View duplicate group details
- /duplicates/select-primary/<group_id>/<photo_id>/ - Select primary photo in a group
- /duplicates/group/<id>/delete-photos/ - Delete duplicate photos
 