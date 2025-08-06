# SnapFlow: Intelligent Event Photo Management Platform

[![Django](https://img.shields.io/badge/Django-5.1.6-green.svg)](https://docs.djangoproject.com/en/5.1/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![AI-Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](#ai-features)

## Overview

SnapFlow is a comprehensive Django-based web application designed to revolutionize event photo management through advanced AI-powered features. The platform provides intelligent photo organization, face recognition, privacy controls, and personalized galleries for event participants.

## Core Features

### AI-Powered Photo Intelligence

- **Advanced Face Recognition**: Automatic face detection and participant identification using DeepFace and MediaPipe
- **Quality Assessment**: AI-driven photo quality scoring and best shot selection
- **Duplicate Detection**: Intelligent duplicate photo identification and management
- **Scene Tagging**: Automatic image categorization and tagging
- **Smart Highlights**: AI-curated photo highlights by category (OVERALL, PORTRAIT, GROUP, ACTION, COMPOSITION, LIGHTING)

### Flexible User Management

- **Event Organizers**: Complete event lifecycle management, crew coordination, participant management
- **Photographers**: Professional tools for photo upload, processing, and gallery management
- **Participants**: Personalized photo galleries with face-based filtering

### Privacy-First Architecture

- **Granular Privacy Controls**: Individual photo visibility settings
- **Face Blurring Technology**: AI-powered privacy protection
- **Privacy Request Workflow**: User-initiated privacy requests with organizer approval
- **GDPR Compliance**: Data protection and user consent management

### Intelligent Notification System

- **Multi-Channel Notifications**: Email and in-app notifications
- **Smart Batching**: Morning and evening email batches to reduce spam
- **Digest Options**: Daily and weekly notification digests
- **Event-Based Alerts**: Real-time updates for events, photos, and user interactions

### Quick Registration System

- **QR Code Generation**: Dynamic QR codes for easy event registration
- **Event Cards**: Professional event invitation cards (Image/PDF formats)
- **Bulk Registration**: Streamlined participant onboarding

## Technology Stack

### Backend Framework

- **Django 5.1.6**: Modern web framework with robust ORM and security features
- **Celery 5.4.0**: Distributed task queue for background processing
- **Redis**: Message broker and caching layer

### AI & Computer Vision

- **OpenCV 4.10.0**: Computer vision and image processing
- **face_recognition 1.3.0**: High-accuracy face recognition
- **DeepFace 0.0.93**: Advanced facial analysis and verification
- **MediaPipe 0.10.14**: Real-time face detection and landmarks
- **TensorFlow 2.18.0**: Deep learning framework for AI models
- **scikit-image 0.24.0**: Image processing algorithms

### Image Processing & Enhancement

- **Pillow 11.0.0**: Python Imaging Library for image manipulation
- **NumPy 1.26.4**: Numerical computing for image arrays
- **SciPy 1.14.1**: Scientific computing and image processing
- **ImageHash 4.3.2**: Perceptual image hashing for duplicates

### Frontend & UI

- **Bootstrap 5**: Responsive CSS framework
- **Django Crispy Forms**: Enhanced form rendering
- **Easy Thumbnails**: Automatic image thumbnail generation

### Development & Utilities

- **Django Extensions**: Additional management commands and utilities
- **QRCode 8.0**: QR code generation for quick registration
- **ReportLab 4.3.1**: PDF generation for event cards
- **Jupyter**: Interactive development and data analysis

## System Architecture

SnapFlow is built with a modular Django app architecture for scalability and maintainability:

### Core Django Apps

1. **Users App** (`users/`)

   - Custom user authentication with role-based access control
   - Three user types: Organizers, Photographers, Participants
   - Profile management with specialized forms for each role
   - Social connections and user relationships
   - Profile completion middleware

2. **Events App** (`events/`)

   - Complete event lifecycle management
   - Event creation, configuration, and themes
   - Crew and participant management
   - Access control and invitation system
   - Gallery access management

3. **Photos App** (`photos/`)

   - Advanced photo upload and processing
   - AI-powered face recognition and tagging
   - Photo quality assessment and scoring
   - User gallery creation and management
   - Photo interactions (likes, comments)
   - Bulk download functionality

4. **Notifications App** (`notifications/`)

   - Multi-channel notification system (email + in-app)
   - Customizable notification preferences
   - Batched email processing to prevent spam
   - Daily and weekly digest functionality
   - Event-driven notification triggers

5. **Highlights App** (`highlights/`)

   - AI-powered best shot selection
   - Photo categorization by quality metrics
   - Duplicate photo detection and management
   - Event highlight curation
   - Quality scoring algorithms

6. **Privacy App** (`privacy/`)

   - Advanced privacy controls and settings
   - User-initiated privacy requests
   - Face blurring and photo processing
   - Organizer approval workflows
   - GDPR compliance features

7. **Quick Registration App** (`quick_registration/`)

   - QR code generation for events
   - Event card creation (Image/PDF)
   - Streamlined participant registration
   - Bulk registration management

8. **Home App** (`home/`)
   - Landing page and public content
   - Contact forms and static pages
   - Real-time statistics display
   - SEO-optimized content

### Data Flow Architecture

```
Event Creation → Photo Upload → AI Processing → Face Recognition → Gallery Generation → Notifications
     ↓              ↓              ↓              ↓                ↓                 ↓
  User Management → Storage → Background Tasks → Participant Matching → Privacy Control → User Engagement
```

## Installation & Setup

### Prerequisites

- **Python 3.9+** with pip package manager
- **Git** for version control
- **Redis** server for Celery task queue (optional for development)
- **Virtual environment** (recommended: `venv` or `conda`)

### Quick Start Guide

#### 1. Clone the Repository

```bash
git clone https://github.com/iammnandu/snapflow-ai.git
cd snapflow-ai
```

#### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Note: Some packages like dlib may require additional system dependencies
# On Windows, you may need Visual Studio Build Tools
# On Ubuntu/Debian: sudo apt-get install build-essential cmake
# On macOS: Install Xcode command line tools
```

#### 4. Database Setup

```bash
# Run initial migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser
```

#### 5. Static Files Configuration

```bash
# Collect static files (for production)
python manage.py collectstatic --noinput
```

#### 6. Start Development Server

```bash
# Start Django development server
python manage.py runserver

# Access the application at http://127.0.0.1:8000/
```

### Background Task Processing (Optional)

For full functionality including AI processing and notifications:

#### 1. Install and Start Redis

```bash
# On Windows (using Chocolatey)
choco install redis-64

# On Ubuntu/Debian
sudo apt-get install redis-server

# On macOS
brew install redis
```

#### 2. Start Celery Workers

```bash
# Start Celery worker (in a new terminal)
celery -A SnapFlow worker --loglevel=info

# Start Celery Beat for scheduled tasks (in another terminal)
celery -A SnapFlow beat --loglevel=info

# Optional: Start Flower for task monitoring
celery -A SnapFlow flower
```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following configurations:

```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True  # Set to False in production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database Configuration (for production)
DATABASE_URL=postgresql://user:password@localhost:5432/snapflow

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI Model Configuration
FACE_RECOGNITION_TOLERANCE=0.6
QUALITY_SCORE_THRESHOLD=0.7
```

### Media Files Setup

The application handles various media files:

```python
# Directory structure will be created automatically
media/
├── events/              # Event-related images
├── profile_pics/        # User avatars
├── event_covers/        # Event cover images
├── event_logos/         # Event logos
├── qrcodes/            # Generated QR codes
├── event_cards/        # Event invitation cards
├── debug_faces/        # Face recognition debug images
└── privacy_processed/  # Privacy-processed images
```

### Celery Task Configuration

Configure scheduled tasks in `SnapFlow/celery.py`:

- **Morning Email Batch**: 9:00 AM daily
- **Evening Email Batch**: 5:00 PM daily
- **Daily Digest**: 6:00 PM daily
- **Weekly Digest**: 10:00 AM every Sunday

## AI Features & Capabilities

### Face Recognition Pipeline

```
Photo Upload → Face Detection → Face Encoding → Participant Matching → Gallery Assignment
```

**Technologies Used:**

- **Primary**: `face_recognition` library with dlib backend
- **Secondary**: DeepFace for advanced analysis
- **Detection**: MediaPipe for real-time face detection
- **Fallback**: OpenCV Haar cascades for robust detection

### Photo Quality Assessment

The AI system evaluates photos across multiple dimensions:

- **Sharpness Analysis**: Laplacian variance for blur detection
- **Exposure Evaluation**: Histogram analysis for proper lighting
- **Composition Scoring**: Rule of thirds and subject positioning
- **Face Quality**: Clear face detection and expression analysis
- **Technical Metrics**: Resolution, aspect ratio, file integrity

### Intelligent Categorization

Photos are automatically categorized into:

- **OVERALL**: Best overall shots across all criteria
- **PORTRAIT**: Individual portraits with clear faces
- **GROUP**: Multiple people in frame
- **ACTION**: Movement and activity shots
- **COMPOSITION**: Well-composed artistic shots
- **LIGHTING**: Excellent lighting conditions

### Duplicate Detection

Advanced duplicate detection using:

- **Perceptual Hashing**: ImageHash library for visual similarity
- **Feature Matching**: SIFT/ORB keypoint detection
- **Histogram Comparison**: Color distribution analysis
- **Metadata Analysis**: EXIF data comparison

### Privacy Protection AI

- **Automatic Face Blurring**: Gaussian blur application to detected faces
- **Smart Cropping**: Intelligent cropping to remove unwanted elements
- **Selective Processing**: User-controlled privacy application

## Privacy and Security

### Data Protection Framework

- **Role-Based Access Control**: Granular permissions for different user types
- **Event-Level Privacy**: Public, private, and invite-only events
- **Photo-Level Controls**: Individual photo visibility settings
- **Face-Based Privacy**: Automated face blurring and recognition opt-out

### Security Features

- **CSRF Protection**: Built-in Django CSRF middleware
- **SQL Injection Prevention**: Django ORM parameterized queries
- **XSS Protection**: Template auto-escaping and input sanitization
- **File Upload Security**: Image validation and secure file handling
- **Session Security**: Secure session management and timeout

### GDPR Compliance

- **User Consent Management**: Explicit consent for face recognition
- **Data Portability**: Export user data and photos
- **Right to Deletion**: Complete data removal on request
- **Data Minimization**: Only collect necessary information
- **Privacy by Design**: Default privacy-preserving settings

### Privacy Request Workflow

1. **User Initiates**: Privacy request through the interface
2. **Organizer Review**: Event organizer reviews and approves/denies
3. **Automated Processing**: System applies privacy settings
4. **Notification**: All parties notified of completion

## Usage Guide

### For Event Organizers

1. **Create Event**: Set up event details, themes, and configurations
2. **Manage Crew**: Invite photographers and assign roles
3. **Add Participants**: Bulk import or individual participant management
4. **Generate QR Codes**: Create quick registration links and event cards
5. **Monitor Progress**: Track photo uploads and AI processing
6. **Review Privacy Requests**: Approve/deny participant privacy requests

### For Photographers

1. **Accept Crew Invitation**: Join events as lead or assistant photographer
2. **Upload Photos**: Bulk photo upload with automatic processing
3. **Monitor AI Analysis**: View quality scores and categorization
4. **Manage Gallery**: Organize and curate photo collections
5. **Handle Duplicates**: Review and manage duplicate photo groups

### For Participants

1. **Register for Events**: Use QR codes or registration links
2. **View Personal Gallery**: Access photos featuring yourself
3. **Interact with Photos**: Like, comment, and download photos
4. **Privacy Controls**: Request photo removal or face blurring
5. **Download Photos**: Bulk download personal photo collections

## Database Schema

### Core Models Overview

```sql
-- User Management
CustomUser (id, username, email, role, avatar, phone_number, ...)
SocialConnection (user, platform, profile_url, ...)

-- Event Management
Event (id, title, slug, organizer, event_type, status, ...)
EventCrew (event, member, role, invited_at, ...)
EventParticipant (event, user, participant_type, ...)

-- Photo Management
EventPhoto (id, event, image, uploaded_by, processed, quality_score, ...)
UserPhotoMatch (user, photo, confidence_score, ...)
PhotoLike (user, photo, created_at)
PhotoComment (user, photo, content, created_at)

-- AI & Analytics
BestShot (event, photo, category, score, ...)
DuplicateGroup (event, primary_photo, ...)
DuplicatePhoto (group, photo, similarity_score)

-- Privacy & Notifications
PrivacyRequest (user, event, request_type, status, ...)
Notification (recipient, notification_type, content, ...)
NotificationPreference (user, email_*, app_*, ...)
```

## API Endpoints

### Event Management

- `GET/POST /events/` - List/Create events
- `GET/PUT/DELETE /events/{slug}/` - Event details
- `POST /events/{slug}/participants/add/` - Add participants
- `GET /events/{slug}/gallery/` - Event photo gallery

### Photo Management

- `POST /photos/{slug}/upload/` - Upload photos
- `GET /photos/my-gallery/` - User personal gallery
- `POST /photos/photo/{id}/action/` - Like/unlike photos
- `GET /photos/event/{slug}/download/` - Download event photos

### AI Processing

- `POST /photos/event/{slug}/reanalyze-all/` - Reprocess all photos
- `GET /highlights/events/{slug}/highlights/` - Get best shots
- `GET /highlights/events/{slug}/duplicates/` - View duplicates

### Privacy & Security

- `POST /privacy/event/{slug}/request/` - Create privacy request
- `GET /privacy/requests/` - View user privacy requests
- `POST /privacy/requests/{id}/respond/` - Respond to requests

## Testing

### Run Test Suite

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test events
python manage.py test photos
python manage.py test users

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

### Test Categories

- **Unit Tests**: Model methods and utilities
- **Integration Tests**: View functionality and workflows
- **AI Processing Tests**: Face recognition and quality assessment
- **Security Tests**: Authentication and authorization
- **Performance Tests**: Large file upload and processing

## Performance Optimization

### Image Processing

- **Lazy Loading**: Photos loaded on demand
- **Thumbnail Generation**: Multiple sizes for responsive display
- **CDN Integration**: Static file delivery optimization
- **Compression**: Automatic image compression for web delivery

### Database Optimization

- **Query Optimization**: Select_related and prefetch_related usage
- **Database Indexing**: Strategic indexes on frequent lookups
- **Connection Pooling**: Efficient database connection management
- **Caching**: Redis caching for frequently accessed data

### Background Processing

- **Async Tasks**: Celery for heavy AI processing
- **Task Prioritization**: Critical tasks processed first
- **Batch Processing**: Bulk operations for efficiency
- **Error Handling**: Robust retry mechanisms

## Deployment

### Production Environment Setup

#### 1. Server Requirements

- **CPU**: Multi-core processor (AI processing intensive)
- **RAM**: Minimum 8GB (16GB+ recommended)
- **Storage**: SSD with sufficient space for media files
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2

#### 2. Production Dependencies

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-pip python3-venv postgresql nginx redis-server

# Install Python dependencies
pip install gunicorn psycopg2-binary
```

#### 3. Environment Configuration

```bash
# Set production environment variables
export DJANGO_SETTINGS_MODULE=SnapFlow.settings.production
export SECRET_KEY=your-production-secret-key
export DEBUG=False
export DATABASE_URL=postgresql://user:pass@localhost/snapflow_prod
```

#### 4. Web Server Configuration (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/snapflow/static/;
    }

    location /media/ {
        alias /path/to/snapflow/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 5. Process Management

```bash
# Use supervisor or systemd for process management
sudo systemctl enable snapflow
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat
```

## Contributing

We welcome contributions to SnapFlow! Here's how you can help:

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Contribution Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR
- Use meaningful commit messages

### Areas for Contribution

- **AI Models**: Improve face recognition accuracy
- **Performance**: Optimize image processing workflows
- **UI/UX**: Enhance user interface and experience
- **Security**: Strengthen security measures
- **Documentation**: Improve code documentation
- **Testing**: Expand test coverage

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Django Community**: For the excellent web framework
- **OpenCV Contributors**: For computer vision capabilities
- **face_recognition Library**: For reliable face recognition
- **DeepFace Project**: For advanced facial analysis
- **Celery Team**: For distributed task processing
- **Bootstrap Team**: For responsive UI components

## Support & Contact

### Getting Help

- **Documentation**: Check this README and inline code documentation
- **Issues**: Report bugs and feature requests on GitHub Issues
- **Discussions**: Join community discussions on GitHub Discussions

### Contact Information

- **Developer**: Nandu Rajesh
- **Email**: iamnandurajesh@gmail.com
- **GitHub**: [@iammnandu](https://github.com/iammnandu)
- **Project Repository**: [snapflow-ai](https://github.com/iammnandu/snapflow-ai)

### Reporting Security Issues

For security vulnerabilities, please email directly rather than opening a public issue.

---

**Made with dedication for event photography communities worldwide**
