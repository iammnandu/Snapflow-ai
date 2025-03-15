# Users App

## Models

**CustomUser Model**
- Extends Django's AbstractUser
- role (ORGANIZER, PHOTOGRAPHER, PARTICIPANT)
- avatar, phone_number (common fields)
- company_name, website (organizer fields)
- portfolio_url, photographer_role, watermark (photographer fields)
- participant_type, image_visibility, blur_requested, remove_requested, is_verified (participant fields)

## Forms

- **BasicRegistrationForm**: Username, email, password fields
- **OrganizerProfileForm**: Avatar, phone, company, website
- **PhotographerProfileForm**: Avatar, phone, portfolio, role, watermark
- **ParticipantProfileForm**: Avatar, phone, participant type, visibility, privacy requests
- **UserTypeSelectionForm**: Role selection

## Views

### Authentication
- **register**: User registration with role selection
- **complete_profile**: Role-specific profile completion
- **logout_view**: Custom logout

### Profile Management
- **ProfileView**: Display user profile 
- **ProfileUpdateView**: Update profile data
- **update_privacy**: Update privacy settings
- **delete_account**: Delete user account

### Dashboards
- **dashboard**: Role-specific dashboard views
  - Organizer: Events, participants stats, pending requests
  - Photographer: Assignments, photo statistics, upload data
  - Participant: Event participations, photos

## Key URLs
- /register/ - User registration
- /profile/ - View profile
- /profile/update/ - Update profile
- /complete-profile/ - Complete profile setup
- /login/, /logout/ - Authentication
- /dashboard/ - User dashboard
- /privacy/update/ - Update privacy settings
- /delete-account/ - Delete account

## Middleware

**ProfileCompletionMiddleware**
- Enforces profile completion by redirecting users with incomplete profiles
- Excludes specific URLs from redirection
- Performs role-specific completeness checks

## Signals
- **User creation signal**: Sends role-specific welcome emails
- **Profile update signal**: Notifies admins about photographer verification needs

## Integration Points
- Connects with events app for event access and participation
- Interfaces with photos app for dashboard statistics