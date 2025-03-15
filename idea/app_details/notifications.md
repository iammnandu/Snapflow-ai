# notifications

## App Overview
The "notifications" app is designed to manage and deliver notifications to users within the application. It supports both in-app notifications and email notifications for various events such as photo uploads, comments, likes, event invitations, and more. Users can customize their notification preferences to control what types of notifications they receive.

## Models
**Notification Model**
- Key fields:
  - `recipient`: Foreign key to the user receiving the notification
  - `notification_type`: Type of notification (e.g., photo upload, comment)
  - `is_read`: Boolean indicating if the notification has been read
  - `content_object`: Generic foreign key to the object related to the notification (e.g., a photo or event)
- Special fields/behaviors:
  - `get_absolute_url`: Returns a URL related to the notification content

**NotificationPreference Model**
- Key fields:
  - `user`: OneToOneField with the user
  - Various fields for toggling different types of email and in-app notifications
  - Fields for opting into daily or weekly digest emails
- Special fields/behaviors:
  - `NotificationPreferenceForm` is used to update these preferences

## Forms
- **NotificationPreferenceForm**: Allows users to customize their notification preferences, including toggles for different notification types and digest options.

## Views
### Notification Views
- **notification_list**: Displays a list of a user's notifications, allowing filtering by type and read status.
- **notification_detail**: Displays details of a single notification and marks it as read.
- **mark_all_as_read**: Marks all notifications for a user as read.
- **mark_as_read**: Marks a specific notification as read.
- **delete_notification**: Deletes a specific notification.
- **preferences**: Allows users to view and update their notification preferences.

## Key URLs
- `/notifications/`: Lists all notifications for the user.
- `/notifications//`: Displays details of a specific notification.
- `/notifications//mark-read/`: Marks a notification as read.
- `/notifications//delete/`: Deletes a notification.
- `/notifications/mark-all-read/`: Marks all notifications as read.
- `/notifications/preferences/`: Manages notification preferences.


## Context Processors
- **notification_processor**: Injects notification data (unread count and recent notifications) into the context for all templates.

## Signals
- **post_save** signals are used to trigger notifications for various events:
  - `EventPhoto` creation: Triggers a notification for photo uploads.
  - `UserPhotoMatch` creation: Triggers a notification for face recognition.
  - `PhotoComment` creation: Triggers a notification for comments.
  - `PhotoLike` creation: Triggers a notification for likes.
  - `EventCrew` and `EventParticipant` creation: Triggers notifications for crew and participant invitations.
  - `EventAccessRequest` creation and status change: Triggers notifications for access requests and approvals.

## Handlers

- **NotificationHandler**: Encapsulates the logic for creating notifications based on different events.
  - **handle_photo_upload**: Handles creating notifications when a photo is uploaded.
  - **handle_face_recognition**: Handles creating notifications when a face is recognized in a photo.
  - **handle_photo_comment**: Handles creating notifications when a photo receives a comment.
  - **handle_photo_like**: Handles creating notifications when a photo receives a like.
  - **handle_event_invitation**: Handles creating notifications when a user is invited to an event.
  - **handle_participant_invitation**: Handles creating notifications when a user is invited as a participant.
  - **handle_access_request**: Handles creating notifications when an access request is made.
  - **handle_request_approved**: Handles creating notifications when an access request is approved.

## Services

- **NotificationService**: Contains methods for core notification operations.
  - **mark_all_as_read**: Marks all notifications for a user as read.
  - **\_send_email_notification**: Sends a single notification via email.
  - **\_send_digest_email**: Sends a digest email (daily or weekly) to a user containing a summary of their notifications.

## Tasks
- **send_notification_email**: Sends an email for a specific notification.
- **send_daily_digest**: Sends a daily digest email to users who have opted in.
- **send_weekly_digest**: Sends a weekly digest email to users who have opted in.

## Integration Points
- **Photos App**: Integrates with the photos app for photo-related notifications.
- **Events App**: Integrates with the events app for event-related notifications.
- **User App**: Integrates with the user model for user-specific notifications.

