# events/forms.py
from django import forms
from .models import Event, EventCrew, EventParticipant, EventConfiguration
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class EventCreationForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title', 'event_type', 'description', 'start_date', 
            'end_date', 'timezone', 'location', 'is_public', 
            'require_registration', 'logo', 'cover_image'
        ]
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class EventConfigurationForm(forms.ModelForm):
    class Meta:
        model = EventConfiguration
        exclude = ['event', 'created_at', 'updated_at']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['allowed_formats'].widget = forms.CheckboxSelectMultiple(
            choices=[('jpg', 'JPG'), ('png', 'PNG'), ('heic', 'HEIC')]
        )

class CrewInvitationForm(forms.ModelForm):
    email = forms.EmailField(label=_("Photographer's Email"))
    
    class Meta:
        model = EventCrew
        fields = ['role', 'notes', 'assigned_area']

class ParticipantInvitationForm(forms.ModelForm):
    emails = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text=_("Enter one email per line")
    )
    
    class Meta:
        model = EventParticipant
        fields = ['participant_type']

    def clean_emails(self):
        emails = self.cleaned_data['emails'].split('\n')
        cleaned_emails = [email.strip() for email in emails if email.strip()]
        
        # Validate each email
        for email in cleaned_emails:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError(f'Invalid email: {email}')
        
        return cleaned_emails

class EventThemeForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['theme', 'primary_color', 'secondary_color']
        widgets = {
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color'}),
        }

class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = EventConfiguration
        fields = [
            'enable_download', 'download_watermark',
            'enable_face_grouping', 'enable_scene_detection',
            'notify_on_upload', 'notify_on_comment'
        ]

class EventAccessRequestForm(forms.Form):
    event_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit event code'}),
        validators=[RegexValidator(r'^[A-Z0-9]{6}$', message="Invalid format. Use only letters and numbers.")],
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Optional message to the event organizer'
    )

    def clean_event_code(self):
        code = self.cleaned_data['event_code'].upper()
        try:
            event = Event.objects.get(event_code=code)
            self.cleaned_data['event'] = event
            return code
        except Event.DoesNotExist:
            raise forms.ValidationError('Invalid event code')
