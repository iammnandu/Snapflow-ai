# notifications/handlers.py
from django.urls import reverse
from .services import NotificationService

class NotificationHandler:
    @staticmethod
    def handle_photo_upload(photo):
        """Notify relevant users when a new photo is uploaded"""
        event = photo.event
        photographer = photo.uploaded_by
        
        # Notify event organizer
        if event.organizer != photographer:
            try:
                notification = NotificationService.create_notification(
                    recipient=event.organizer,
                    notification_type='new_photo',
                    title=f"New photo uploaded for {event.title}",
                    message=f"{photographer.get_full_name()} has uploaded a new photo to your event.",
                    related_object=photo,
                    from_user=photographer,
                    action_url=reverse('photos:detail', kwargs={'pk': photo.id})
                )
            except Exception as e:
                import traceback
                print(f"Error in handle_photo_upload: {e}")
                traceback.print_exc()
                
    @staticmethod
    def handle_face_recognition(photo_match):
        """Notify user when their face is recognized in a photo"""
        photo = photo_match.photo
        user = photo_match.user
        event = photo.event
        
        try:
            NotificationService.create_notification(
                recipient=user,
                notification_type='face_recognized',
                title=f"You were recognized in a photo",
                message=f"You were identified in a new photo from the event '{event.title}'.",
                related_object=photo,
                action_url=reverse('photos:photo_detail', kwargs={'pk': photo.id})
            )
        except Exception as e:
            import traceback
            print(f"Error in handle_face_recognition: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_photo_comment(comment):
        """Notify relevant users about a new comment"""
        photo = comment.photo
        commenter = comment.user
        
        try:
            # Notify photo uploader
            if photo.uploaded_by != commenter:
                NotificationService.create_notification(
                    recipient=photo.uploaded_by,
                    notification_type='comment',
                    title=f"New comment on your photo",
                    message=f"{commenter.get_full_name()} commented on your photo from {photo.event.title}.",
                    related_object=comment,
                    from_user=commenter,
                    action_url=reverse('photos:photo_detail', kwargs={'pk': photo.id})
                )
            
            # Notify event organizer if different
            if photo.event.organizer != commenter and photo.event.organizer != photo.uploaded_by:
                NotificationService.create_notification(
                    recipient=photo.event.organizer,
                    notification_type='comment',
                    title=f"New comment on event photo",
                    message=f"{commenter.get_full_name()} commented on a photo from {photo.event.title}.",
                    related_object=comment,
                    from_user=commenter,
                    action_url=reverse('photos:photo_detail', kwargs={'pk': photo.id})
                )
        except Exception as e:
            import traceback
            print(f"Error in handle_photo_comment: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_photo_like(like):
        """Notify photo uploader about a new like"""
        photo = like.photo
        liker = like.user
        
        try:
            # Only notify if liker is different from uploader
            if photo.uploaded_by != liker:
                NotificationService.create_notification(
                    recipient=photo.uploaded_by,
                    notification_type='like',
                    title=f"New like on your photo",
                    message=f"{liker.get_full_name()} liked your photo from {photo.event.title}.",
                    related_object=like,
                    from_user=liker,
                    action_url=reverse('photos:photo_detail', kwargs={'pk': photo.id})
                )
        except Exception as e:
            import traceback
            print(f"Error in handle_photo_like: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_event_invitation(event_crew):
        """Notify photographer about event crew invitation"""
        event = event_crew.event
        photographer = event_crew.member
        
        try:
            NotificationService.create_notification(
                recipient=photographer,
                notification_type='event_invite',
                title=f"You've been invited to photograph an event",
                message=f"{event.organizer.get_full_name()} has invited you to join the crew for '{event.title}'.",
                related_object=event,
                from_user=event.organizer,
                action_url=reverse('events:event_dashboard', kwargs={'slug': event.slug} if hasattr(event, 'slug') and event.slug else {'pk': event.id})
            )
        except Exception as e:
            import traceback
            print(f"Error in handle_event_invitation: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_participant_invitation(event_participant):
        """Notify participant about event invitation"""
        event = event_participant.event
        participant = event_participant.user
        
        try:
            if participant:  # Only if user account exists
                NotificationService.create_notification(
                    recipient=participant,
                    notification_type='event_invite',
                    title=f"You've been invited to an event",
                    message=f"{event.organizer.get_full_name()} has invited you to '{event.title}'.",
                    related_object=event,
                    from_user=event.organizer,
                    action_url=reverse('events:event_dashboard', kwargs={'slug': event.slug} if hasattr(event, 'slug') and event.slug else {'pk': event.id})
                )
        except Exception as e:
            import traceback
            print(f"Error in handle_participant_invitation: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_event_update(event, update_message):
        """Notify all event participants and crew about event updates"""
        # Get all users associated with the event
        participants = [p.user for p in event.participants.all() if p.user]
        crew_members = [c.member for c in event.crew_members.all()]
        
        # Combine and remove duplicates
        all_users = list(set(participants + crew_members))
        
        try:
            # Notify each user
            for user in all_users:
                NotificationService.create_notification(
                    recipient=user,
                    notification_type='event_update',
                    title=f"Event update: {event.title}",
                    message=update_message,
                    related_object=event,
                    from_user=event.organizer,
                    action_url=reverse('events:event_dashboard', kwargs={'slug': event.slug} if hasattr(event, 'slug') and event.slug else {'pk': event.id})
                )
        except Exception as e:
            import traceback
            print(f"Error in handle_event_update: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_access_request(access_request):
        """Notify organizer about access requests"""
        event = access_request.event
        requester = access_request.user
        
        try:
            NotificationService.create_notification(
                recipient=event.organizer,
                notification_type='access_request',
                title=f"New access request for {event.title}",
                message=f"{requester.get_full_name()} has requested access to your event.",
                related_object=access_request,
                from_user=requester,
                action_url=reverse('events:access_requests', kwargs={'slug': event.slug} if hasattr(event, 'slug') and event.slug else {'pk': event.id})
            )
        except Exception as e:
            import traceback
            print(f"Error in handle_access_request: {e}")
            traceback.print_exc()
    
    @staticmethod
    def handle_request_approved(access_request):
        """Notify user when their access request is approved"""
        event = access_request.event
        requester = access_request.user
        
        try:
            NotificationService.create_notification(
                recipient=requester,
                notification_type='request_approved',
                title=f"Access granted to {event.title}",
                message=f"Your request to access '{event.title}' has been approved.",
                related_object=event,
                from_user=event.organizer,
                action_url=reverse('events:event_dashboard', kwargs={'slug': event.slug} if hasattr(event, 'slug') and event.slug else {'pk': event.id})
            )
        except Exception as e:
            import traceback
            print(f"Error in handle_request_approved: {e}")
            traceback.print_exc()