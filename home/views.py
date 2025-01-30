from django.shortcuts import render
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.core.mail import send_mail
from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)

def index(request):
    return render(request, 'home/index.html')

def landing(request):
    return render(request, 'home/landing.html')

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
    success_url = '/contact/'

    def form_valid(self, form):
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        
        # Send email logic here
        send_mail(
            f'Contact Form: {subject}',
            f'From: {name} <{email}>\n\n{message}',
            email,
            ['admin@snapflow.com'],
            fail_silently=False,
        )
        
        messages.success(self.request, 'Thank you for contacting us!')
        return super().form_valid(form)