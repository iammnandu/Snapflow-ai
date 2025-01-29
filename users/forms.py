from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, UserPreferences

class CustomUserCreationForm(UserCreationForm):
    gdpr_consent = forms.BooleanField(required=True)
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role', 'gdpr_consent')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['avatar', 'bio', 'phone_number', 'website', 'company_name']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.role == CustomUser.Roles.PHOTOGRAPHER:
            self.fields['portfolio_url'] = forms.URLField(required=False)
            self.fields['equipment_details'] = forms.CharField(widget=forms.Textarea, required=False)
            self.fields['expertise'] = forms.CharField(required=False)

class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = ['dark_mode', 'language', 'email_notifications', 'privacy_level', 'auto_face_blur']
