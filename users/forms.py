# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from .models import CustomUser, SocialConnection


phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


class UserTypeSelectionForm(forms.Form):
    role = forms.ChoiceField(
        choices=CustomUser.Roles.choices,
        widget=forms.RadioSelect,
        label="Select User Type"
    )

class BasicRegistrationForm(UserCreationForm):
    """Initial registration form with only basic fields"""
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')


class OrganizerProfileForm(forms.ModelForm):
    """Profile completion form for organizers"""
    avatar_data = forms.CharField(required=False, widget=forms.HiddenInput())
    phone_number = forms.CharField(
        validators=[phone_regex],
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'company_name', 'website']
        widgets = {
            'avatar': forms.HiddenInput(),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # If we have avatar_data, we don't need avatar validation
        if 'avatar_data' in self.data and self.data['avatar_data']:
            if 'avatar' in self._errors:
                del self._errors['avatar']
        return cleaned_data

class PhotographerProfileForm(forms.ModelForm):
    """Profile completion form for photographers"""
    avatar_data = forms.CharField(required=False, widget=forms.HiddenInput())
    phone_number = forms.CharField(
        validators=[phone_regex],
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'portfolio_url', 'photographer_role', 'watermark']
        widgets = {
            'avatar': forms.HiddenInput(),
            'portfolio_url': forms.URLInput(attrs={'class': 'form-control'}),
            'photographer_role': forms.Select(attrs={'class': 'form-control'}),
            'watermark': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # If we have avatar_data, we don't need avatar validation
        if 'avatar_data' in self.data and self.data['avatar_data']:
            if 'avatar' in self._errors:
                del self._errors['avatar']
        return cleaned_data

class ParticipantProfileForm(forms.ModelForm):
    """Profile completion form for participants"""
    avatar_data = forms.CharField(required=False, widget=forms.HiddenInput())
    phone_number = forms.CharField(
        validators=[phone_regex],
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number']
        widgets = {
            'avatar': forms.HiddenInput(),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # If we have avatar_data, we don't need avatar validation
        if 'avatar_data' in self.data and self.data['avatar_data']:
            if 'avatar' in self._errors:
                del self._errors['avatar']
        return cleaned_data
 
class SocialConnectionForm(forms.ModelForm):
    class Meta:
        model = SocialConnection
        fields = ['username', 'profile_url']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your username on this platform'
            }),
            'profile_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://platform.com/yourusername'
            })
        }