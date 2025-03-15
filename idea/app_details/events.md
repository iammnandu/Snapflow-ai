# Events App Documentation

## Models

**Event Model**
- Core model for managing events with fields like `title`, `slug`, `event_type`, and `description`
- Supports different event types via `EventTypes` choices (WEDDING, BIRTHDAY, CORPORATE, etc.)
- Tracks event status via `EventStatus` choices (DRAFT, ACTIVE, COMPLETED, CANCELLED)
- Stores event details like `start_date`, `end_date`, `timezone`, and `location`
- Includes customization options like `primary_color`, `secondary_color`, `logo`, and `cover_image`
- Manages privacy settings with `is_public`, `require_registration`, and `allow_guest_upload`
- Enables AI features with `enable_face_detection`, `enable_moment_detection`, and `enable_auto_tagging`
- Generates unique `event_code` and `slug` on save
- Related to `EventConfiguration`, `EventTheme`, and linked to users via `organizer`

**EventTheme Model**
- Manages visual theming for events with `name`, `description`, and `template`
- Stores visual settings like `primary_color`, `secondary_color`, and `font_family`
- Includes `thumbnail` for theme preview and `is_active` flag

**EventCrew Model**
- Manages photographers and other crew members for events
- Defines roles via `CrewRoles` choices (LEAD, SECOND, ASSISTANT, VIDEOGRAPHER, etc.)
- Tracks status with `is_confirmed` flag
- Stores crew details like `notes`, `equipment`, and `assigned_area`
- Linked to both `Event` and user models

**EventParticipant Model**
- Manages participants/attendees for events
- Defines types via `ParticipantTypes` choices (GUEST, VIP, SPEAKER, etc.)
- Tracks registration status with `is_registered` flag
- Stores unique `registration_code` for each participant
- Manages privacy preferences with `allow_photos` and `request_blur`
- Can be linked to registered users or just store `email` and `name`

**EventConfiguration Model**
- One-to-one relationship with `Event` to store configuration settings
- Manages gallery settings like `enable_comments`, `enable_likes`, and `enable_download`
- Controls upload settings with `max_upload_size` and `allowed_formats`
- Configures AI processing with `enable_face_grouping`, `enable_scene_detection`, and `enable_quality_filter`
- Handles notification preferences with `notify_on_upload` and `notify_on_comment`

**EventAccessRequest Model**
- Manages requests to access events
- Tracks request status via `RequestStatus` choices (PENDING, APPROVED, REJECTED)
- Stores request type (PHOTOGRAPHER or PARTICIPANT)
- Includes optional `message` field for request details
- Links to both `Event` and user models

## Forms

- **EventCreationForm**: Creates and updates events with fields for basic event details
- **EventConfigurationForm**: Manages event configuration settings
- **CrewInvitationForm**: Invites photographers to events by username with role assignment
- **ParticipantInvitationForm**: Invites participants via email with batch processing
- **EventThemeForm**: Updates event theme and color settings
- **PrivacySettingsForm**: Manages event privacy and notification settings
- **EventAccessRequestForm**: Handles access requests with event code validation

## Views

### Event Management
- **EventCreateView**: Creates new events, validates organizer role, and sets up initial configuration
- **EventSetupView**: Multi-step setup wizard for events (privacy, theme, config)
- **EventDashboardView**: Dynamic dashboard that shows different views based on user role
- **EventListView**: Lists events with filters for event type and status
- **EventUpdateView**: Updates existing event information

### Crew Management
- **CrewManagementView**: Manages event crew with invitation handling
- **accept_crew_invitation**: Processes crew invitation acceptances via signed tokens
- **EquipmentConfigurationView**: Configures equipment for crew members

### Participant Management
- **EventParticipantsView**: Lists and manages event participants
- **AddParticipantView**: Adds new participants to events
- **EditParticipantView**: Updates participant information
- **RemoveParticipantView**: Removes participants from events
- **ResendParticipantInviteView**: Resends invitations to participants
- **create_temp_profile**: Creates temporary participant profiles

### Access Requests
- **RequestEventAccessView**: Form view for requesting event access
- **request_access**: Handles event access requests using event codes
- **access_requests_list**: Lists all access requests for users
- **approve_request**: Approves access requests
- **reject_request**: Rejects access requests
- **cancel_access_request**: Cancels pending access requests

### AI Features
- **toggle_ai_features**: Toggles AI features for events via AJAX

## Key URLs

- `/events/create/` - Create a new event
- `/events/list/` - List all events
- `/events/<slug>/dashboard/` - Event dashboard
- `/events/<slug>/edit/` - Edit event details
- `/events/<slug>/setup/<step>/` - Multi-step event setup
- `/events/<slug>/crew/` - Manage event crew
- `/events/<slug>/participants/` - Manage event participants
- `/events/<slug>/equipment/` - Configure crew equipment
- `/events/<slug>/temp-profile/` - Create temporary participant profile
- `/events/access/request/` - Request access to an event
- `/events/requests/` - List all access requests
- `/events/requests/<id>/approve/` - Approve an access request
- `/events/requests/<id>/reject/` - Reject an access request


## Integration Points

- **User Authentication**: Uses Django's built-in authentication system with `LoginRequiredMixin` and `UserPassesTestMixin`
- **User Roles**: Integrates with a custom user model that has roles (ORGANIZER, PHOTOGRAPHER, etc.)
- **Photo Integration**: Connects with a photos app that handles photo uploads and galleries
- **Notification System**: Configured to send notifications for uploads and comments
- **AI Processing**: Integrates with AI features for face detection, moment detection, and auto-tagging
- **Security**: Uses Django's `TimestampSigner` for secure invitation links