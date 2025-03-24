# privacy/forms.py
from django import forms
from .models import PrivacyRequest

class PrivacyRequestForm(forms.ModelForm):
    """Form for creating privacy requests."""
    
    class Meta:
        model = PrivacyRequest
        fields = ['request_type', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional: explain why you need this privacy measure'}),
        }


class PrivacyRequestResponseForm(forms.ModelForm):
    """Form for organizers to respond to privacy requests."""
    
    class Meta:
        model = PrivacyRequest
        fields = ['status', 'rejection_reason']
        widgets = {
            'rejection_reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'If rejecting, please provide a reason'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit status choices to approved or rejected
        self.fields['status'].choices = [
            ('approved', 'Approve Request'),
            ('rejected', 'Reject Request'),
        ]
        self.fields['rejection_reason'].required = False

