# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

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
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'company_name', 'website']
        widgets = {
            'avatar': forms.HiddenInput(),  # Changed to hidden input
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
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
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'portfolio_url', 'photographer_role', 'watermark']
        widgets = {
            'avatar': forms.HiddenInput(),  # Changed to hidden input
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
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
    
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'image_visibility', 'blur_requested', 'remove_requested']
        widgets = {
            'avatar': forms.HiddenInput(),  # Changed to hidden input
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),

            'image_visibility': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        # If we have avatar_data, we don't need avatar validation
        if 'avatar_data' in self.data and self.data['avatar_data']:
            if 'avatar' in self._errors:
                del self._errors['avatar']
        return cleaned_data