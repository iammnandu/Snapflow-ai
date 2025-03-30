# quick_registration/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.contrib.sites.shortcuts import get_current_site
from django.utils.crypto import get_random_string
from django.contrib.auth import login

from .models import QuickRegistrationLink
from .forms import QuickRegistrationForm, QuickRegistrationLinkForm
from events.models import Event, EventParticipant
from users.models import CustomUser

import uuid
import qrcode
from io import BytesIO


@login_required
def create_registration_link(request, event_slug):
    """Create a quick registration link for an event"""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if the user is the organizer or a crew member
    if event.organizer != request.user and not event.eventcrew_set.filter(member=request.user).exists():
        raise PermissionDenied("You don't have permission to create registration links for this event.")
    
    if request.method == 'POST':
        form = QuickRegistrationLinkForm(request.POST)
        if form.is_valid():
            registration_link = form.save(commit=False)
            registration_link.event = event
            registration_link.code = get_random_string(length=20)
            registration_link.save()
            
            # Generate QR code
            registration_link.generate_qr_code(request)
            
            messages.success(request, "Registration link created successfully.")
            return redirect('events:event_dashboard', slug=event.slug)
    else:
        form = QuickRegistrationLinkForm()
    
    context = {
        'form': form,
        'event': event,
    }
    return render(request, 'quick_registration/create_link.html', context)


@login_required
def manage_registration_links(request, event_slug):
    """Manage quick registration links for an event"""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if the user is the organizer or a crew member
    if event.organizer != request.user and not event.eventcrew_set.filter(member=request.user).exists():
        raise PermissionDenied("You don't have permission to manage registration links for this event.")
    
    registration_links = QuickRegistrationLink.objects.filter(event=event).order_by('-created_at')
    
    context = {
        'event': event,
        'registration_links': registration_links,
    }
    return render(request, 'quick_registration/manage_links.html', context)


@login_required
def regenerate_qr_code(request, link_id):
    """Regenerate QR code for a registration link"""
    registration_link = get_object_or_404(QuickRegistrationLink, id=link_id)
    
    # Check if the user is the organizer or a crew member
    if (registration_link.event.organizer != request.user and 
        not registration_link.event.eventcrew_set.filter(member=request.user).exists()):
        raise PermissionDenied("You don't have permission to manage this registration link.")
    
    # Delete old QR code if exists
    if registration_link.qr_code:
        registration_link.qr_code.delete(save=False)
    
    # Generate new QR code
    registration_link.generate_qr_code(request)
    
    messages.success(request, "QR code regenerated successfully.")
    return redirect('quick_registration:manage_links', event_slug=registration_link.event.slug)


def register_participant(request, code):
    """Register a participant for an event using a quick registration link"""
    # Get the registration link and check if it's valid
    registration_link = get_object_or_404(QuickRegistrationLink, code=code, is_active=True)
    
    # Check if the link has expired
    if registration_link.expires_at and registration_link.expires_at < timezone.now():
        return render(request, 'quick_registration/expired.html')
    
    event = registration_link.event
    
    if request.method == 'POST':
        form = QuickRegistrationForm(request.POST, request.FILES, initial={'event': event})
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            profile_image = form.cleaned_data.get('profile_image')
            password = form.cleaned_data['password']
            
            # Get the username from the form
            username = getattr(form, 'username', name.replace(' ', '_').lower())
            
            # Check if a user with this email already exists
            try:
                user = CustomUser.objects.get(email=email)
                user_exists = True
            except CustomUser.DoesNotExist:
                # Create a new user
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=name.split()[0] if ' ' in name else name,
                    last_name=' '.join(name.split()[1:]) if ' ' in name else '',
                    role='PARTICIPANT',
                    is_active=True
                )
                user_exists = False
                
                if profile_image:
                    user.avatar = profile_image
                
                if phone_number:
                    user.phone_number = phone_number
                
                user.save()

            # Generate a unique registration code
            def generate_unique_reg_code():
                while True:
                    reg_code = get_random_string(length=12)
                    if not EventParticipant.objects.filter(registration_code=reg_code).exists():
                        return reg_code
            
            # Check if participant already exists for this event and email
            try:
                participant = EventParticipant.objects.get(event=event, email=email)
                # Update existing participant
                participant.user = user
                participant.name = name
                participant.is_registered = True
                participant.save()
            except EventParticipant.DoesNotExist:
                # Create new participant with unique registration code
                participant = EventParticipant.objects.create(
                    event=event,
                    email=email,
                    user=user,
                    name=name,
                    participant_type='ATTENDEE',
                    is_registered=True,
                    allow_photos=True,
                    registration_code=generate_unique_reg_code()
                )
            
            # If the user is not already logged in, log them in
            if not request.user.is_authenticated:
                login(request, user)
            
            messages.success(request, f"You have successfully registered for {event.title}!")
            return redirect('events:event_dashboard', slug=event.slug)
    else:
        form = QuickRegistrationForm()
    
    context = {
        'form': form,
        'event': event,
        'registration_link': registration_link,
    }
    return render(request, 'quick_registration/register.html', context)


def download_qr_code(request, link_id):
    """Download QR code for a registration link"""
    registration_link = get_object_or_404(QuickRegistrationLink, id=link_id)
    
    # Check if the user is the organizer or a crew member
    if (not request.user.is_authenticated or 
        (registration_link.event.organizer != request.user and 
         not registration_link.event.eventcrew_set.filter(member=request.user).exists())):
        raise PermissionDenied("You don't have permission to download this QR code.")
    
    if not registration_link.qr_code:
        registration_link.generate_qr_code(request)
    
    response = HttpResponse(registration_link.qr_code, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="event_{registration_link.event.slug}_qrcode.png"'
    return response