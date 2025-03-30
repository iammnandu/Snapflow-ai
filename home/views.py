from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django import forms
from django.urls import reverse_lazy
from events.models import Event
from photos.models import EventPhoto 
from users.models import CustomUser  
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)

def index(request):

    # Get real-time stats for the index page
    stats = {
        'event_types': Event.objects.values('event_type').distinct().count(),
        'photo_count': EventPhoto.objects.count(),
        'user_count': CustomUser.objects.count(),
        'satisfaction': 99,  # This could be from a feedback model if you have one
    }
    
    # Get testimonials - you could add a testimonials model later
    testimonials = [
        {
            'name': 'Michael Roberts',
            'role': 'Wedding Photographer',
            'image': 'home/img/testimonials/testimonials-1.jpg',
            'text': 'SnapFlow has transformed my wedding photography business. The AI editing features save me hours of post-processing time, and my clients love the real-time photo sharing. It\'s become an essential part of my workflow.'
        },
        {
            'name': 'Jennifer Chen',
            'role': 'Corporate Event Manager',
            'image': 'home/img/testimonials/testimonials-4.jpg',
            'text': 'We used SnapFlow for our annual conference with over 1,000 attendees. The automated organization features categorized photos by sessions and speakers perfectly. The privacy controls gave our attendees peace of mind, and the highlight reel was perfect for social media.'
        }
    ]
    
    return render(request, 'home/index.html', {
        'stats': stats,
        'testimonials': testimonials
    })

def get_features(request):
    features = [
        {
            'title': 'AI-Powered Photo Management',
            'description': 'Automatically categorize and organize photos in real-time with our advanced AI system.',
            'icon': 'bi-camera-reels'
        },
        {
            'title': 'Real-time Event Coverage',
            'description': 'Instantly upload and share photos during events for immediate access by participants.',
            'icon': 'bi-cloud-upload'
        },
        {
            'title': 'Smart Image Organization',
            'description': 'Intelligent tagging and categorization based on faces, moments, and content.',
            'icon': 'bi-grid-3x3'
        },
        {
            'title': 'Privacy Controls',
            'description': 'Granular privacy settings with face-blurring technology for those who opt out.',
            'icon': 'bi-shield-check'
        },
        {
            'title': 'Collaborative Workflow',
            'description': 'Multi-user platform for event organizers, photographers, and participants.',
            'icon': 'bi-people'
        }
    ]
    return render(request, 'home/features.html', {'features': features})

def get_maintanence_page(request):
    return render(request, 'home/under_maintanence.html')

class AboutView(TemplateView):
    template_name = 'home/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['features'] = [
            'AI-Powered Photo Management',
            'Real-time Event Coverage',
            'Smart Image Organization',
            'Privacy Controls',
            'Collaborative Workflow'
        ]
        return context
    


class ContactView(FormView):
    template_name = 'home/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('home:contact')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_info'] = {
            'address': 'Cochi Dhanushkodi Road, Varikoli, Puthenkurish, Kochi, Kerala 682308 ',
            'phone': '+91 8547193672',
            'email': 'snapflow.service@gmail.com'
        }
        return context
    
    def form_valid(self, form):
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        
        # Create email context
        email_context = {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
            'date': timezone.now().strftime("%B %d, %Y at %H:%M")
        }
        
        # Create HTML email
        html_content = render_to_string('email/contact_form_email.html', email_context)
        text_content = strip_tags(html_content)  # Create plain text version for email clients that don't support HTML
        
        try:
            # Create email message with both HTML and plain text versions
            email = EmailMultiAlternatives(
                f'SnapFlow Contact: {subject}',
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            messages.success(self.request, 'Thank you for contacting us! We will get back to you soon.')
        except Exception as e:
            messages.error(self.request, f'There was an error sending your message. Please try again later.')
            
        return super().form_valid(form)