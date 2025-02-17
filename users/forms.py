from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class UserTypeSelectionForm(forms.Form):
    role = forms.ChoiceField(
        choices=CustomUser.Roles.choices,
        widget=forms.RadioSelect,
        label="Select User Type"
    )

class BaseRegistrationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

class OrganizerRegistrationForm(BaseRegistrationForm):
    class Meta(BaseRegistrationForm.Meta):
        fields = BaseRegistrationForm.Meta.fields + ('company_name', 'website')

class PhotographerRegistrationForm(BaseRegistrationForm):
    class Meta(BaseRegistrationForm.Meta):
        fields = BaseRegistrationForm.Meta.fields + ('portfolio_url', 'photographer_role')

class ParticipantRegistrationForm(BaseRegistrationForm):
    class Meta(BaseRegistrationForm.Meta):
        fields = BaseRegistrationForm.Meta.fields + ('participant_type', 'image_visibility')

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.role == CustomUser.Roles.ORGANIZER:
            self.fields['company_name'] = forms.CharField(required=True)
            self.fields['website'] = forms.URLField(required=False)
        
        elif self.instance.role == CustomUser.Roles.PHOTOGRAPHER:
            self.fields['portfolio_url'] = forms.URLField(required=True)
            self.fields['photographer_role'] = forms.ChoiceField(
                choices=CustomUser.PhotographerRoles.choices,
                required=True
            )
            self.fields['watermark'] = forms.ImageField(required=False)
        
        elif self.instance.role == CustomUser.Roles.PARTICIPANT:
            self.fields['participant_type'] = forms.ChoiceField(
                choices=CustomUser.ParticipantTypes.choices,
                required=True
            )
            self.fields['image_visibility'] = forms.ChoiceField(
                choices=[
                    ('PUBLIC', 'Public'),
                    ('PRIVATE', 'Private'),
                    ('EVENT_ONLY', 'Event Only')
                ],
                required=True
            )
            self.fields['blur_requested'] = forms.BooleanField(required=False)
            self.fields['remove_requested'] = forms.BooleanField(required=False)