from django import forms
from .models import NotificationPreference

class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        exclude = ['user']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Group fields for better organization
        self.email_fields = [field for field in self.fields if field.startswith('email_')]
        self.in_app_fields = [field for field in self.fields if field.startswith('notify_')]
        self.digest_fields = [field for field in self.fields if field.startswith('receive_')]
        
        # Add help texts and labels
        for field in self.fields:
            if field.startswith('email_'):
                self.fields[field].label = f"Email for {field.replace('email_', '').replace('_', ' ')}"
                self.fields[field].help_text = "Receive email notifications for this event"
                
            elif field.startswith('notify_'):
                self.fields[field].label = f"Notify for {field.replace('notify_', '').replace('_', ' ')}"
                self.fields[field].help_text = "Receive in-app notifications for this event"