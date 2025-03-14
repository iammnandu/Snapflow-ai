# notifications/forms.py
from django import forms
from .models import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            # Email notification toggles
            'email_event_invites': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_photo_tags': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_likes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_new_photos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_event_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_crew_assignments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # In-app notification toggles
            'app_event_invites': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_photo_tags': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_comments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_likes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_new_photos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_event_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_crew_assignments': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Digest options
            'receive_daily_digest': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_weekly_digest': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Define better field labels for clarity
        notification_type_labels = {
            'event_invites': 'Event Invitations',
            'photo_tags': 'Photo Tags',
            'comments': 'Comments on Your Content',
            'likes': 'Likes on Your Content',
            'new_photos': 'New Photos Added',
            'event_updates': 'Event Updates',
            'crew_assignments': 'Crew Assignments',
        }
        
        # Apply better labels
        for field_type in ['email', 'app']:
            for notification_type, label in notification_type_labels.items():
                field_name = f"{field_type}_{notification_type}"
                if field_name in self.fields:
                    self.fields[field_name].label = label
        
        # Define field categories
        email_field_names = [
            'email_event_invites', 'email_photo_tags', 'email_comments',
            'email_likes', 'email_new_photos', 'email_event_updates',
            'email_crew_assignments'
        ]
        
        app_field_names = [
            'app_event_invites', 'app_photo_tags', 'app_comments',
            'app_likes', 'app_new_photos', 'app_event_updates',
            'app_crew_assignments'
        ]
        
        digest_field_names = [
            'receive_daily_digest', 'receive_weekly_digest'
        ]
        
        # Create field collections with actual field objects
        self.email_fields = [self[name] for name in email_field_names]
        self.app_fields = [self[name] for name in app_field_names]
        self.digest_fields = [self[name] for name in digest_field_names]
        
        # Add help text
        self.fields['receive_daily_digest'].help_text = "Receive a daily summary of all notifications"
        self.fields['receive_weekly_digest'].help_text = "Receive a weekly summary of all notifications"
        
        # Make digest options mutually exclusive (optional)
        self.fields['receive_weekly_digest'].help_text += " (Recommended)"