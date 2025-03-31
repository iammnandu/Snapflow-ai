from django import forms
from django.contrib.auth.password_validation import validate_password
from users.models import CustomUser
from events.models import EventParticipant
from .models import QuickRegistrationLink


class QuickRegistrationForm(forms.Form):
    """Form for participants to quickly register for an event"""
    name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)
    avatar = forms.ImageField(required=False)  # Changed to not required
    avatar_data = forms.CharField(required=False, widget=forms.HiddenInput())
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)
    
    # Rest of the form remains the same
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if this email is already used for a participant in this event
        event = self.initial.get('event')
        
        if event and EventParticipant.objects.filter(event=event, email=email).exists():
            raise forms.ValidationError("This email is already registered for this event.")
            
        return email
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        # Check if name is already used as a username
        username = name.replace(' ', '_').lower()
        if CustomUser.objects.filter(username=username).exists():
            # Append a number if username exists
            base_username = username
            count = 1
            while CustomUser.objects.filter(username=f"{base_username}_{count}").exists():
                count += 1
            username = f"{base_username}_{count}"
            
        self.username = username
        return name
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords don't match")
        
        if password:
            try:
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error('password', error)
                
        return cleaned_data


class QuickRegistrationLinkForm(forms.ModelForm):
    """Form for organizers to create quick registration links"""
    class Meta:
        model = QuickRegistrationLink
        fields = ['is_active', 'expires_at']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }