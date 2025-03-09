# notifications/forms.py
from django import forms
from .models import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user', 'created_at', 'updated_at']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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