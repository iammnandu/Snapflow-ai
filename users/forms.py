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
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'company_name', 'website']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }

class PhotographerProfileForm(forms.ModelForm):
    """Profile completion form for photographers"""
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'portfolio_url', 'photographer_role', 'watermark']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'portfolio_url': forms.URLInput(attrs={'class': 'form-control'}),
            'photographer_role': forms.Select(attrs={'class': 'form-control'}),
            'watermark': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ParticipantProfileForm(forms.ModelForm):
    """Profile completion form for participants"""
    class Meta:
        model = CustomUser
        fields = ['avatar', 'phone_number', 'participant_type', 'image_visibility', 'blur_requested', 'remove_requested']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'participant_type': forms.Select(attrs={'class': 'form-control'}),
            'image_visibility': forms.Select(attrs={'class': 'form-control'}),
        }