# users/views.py
from datetime import timezone
import base64
import logging
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .models import SocialConnection
from photos.models import EventPhoto
from events.models import Event, EventAccessRequest, EventCrew, EventParticipant
from .forms import BasicRegistrationForm, OrganizerProfileForm, ParticipantProfileForm, PhotographerProfileForm, SocialConnectionForm
from django.urls import reverse

logger = logging.getLogger(__name__)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add any additional context needed for the profile template
        context.update({
            'user': user,
            'profile_complete': bool(user.phone_number),  # Basic check for profile completion
        })
        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')
    
    def get_form_class(self):
        form_classes = {
            'ORGANIZER': OrganizerProfileForm,
            'PHOTOGRAPHER': PhotographerProfileForm,
            'PARTICIPANT': ParticipantProfileForm
        }
        return form_classes.get(self.request.user.role)
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!'
            })
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)



def register(request):
    if request.method == 'POST':
        form = BasicRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = request.POST.get('role')
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('users:complete_profile')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')

    else:
        form = BasicRegistrationForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def complete_profile(request):
    user = request.user
    
    form_classes = {
        'ORGANIZER': OrganizerProfileForm,
        'PHOTOGRAPHER': PhotographerProfileForm,
        'PARTICIPANT': ParticipantProfileForm
    }
    
    FormClass = form_classes.get(user.role)
    
    if request.method == 'POST':
        # Create form with POST data and FILES
        form = FormClass(request.POST, request.FILES, instance=user)
        
        # Manually handle the cropped image
        if 'avatar_data' in request.POST and request.POST['avatar_data']:
            try:
                # Get the base64 string from the hidden input
                avatar_data = request.POST['avatar_data']
                
                # Remove the data URL prefix
                if ',' in avatar_data:
                    format_info, avatar_data = avatar_data.split(',', 1)
                
                # Decode base64 data
                avatar_image = base64.b64decode(avatar_data)
                
                # Create a Django file-like object
                avatar_file = ContentFile(avatar_image, name='profile-image.jpg')
                
                # Assign the file to the form instance
                form.instance.avatar = avatar_file
            except Exception as e:
                logger.error(f"Error processing avatar: {str(e)}")
                messages.error(request, f"Error processing profile image: {str(e)}")
        
        # Check form validity and save
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed successfully!')
            return redirect('users:dashboard')
        else:
            # Form is invalid but data will be preserved in the form instance
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FormClass(instance=user)
    
    return render(request, 'users/complete_profile.html', {
        'form': form,
        'user_type': user.get_role_display()
    })

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('users:login')

@login_required
def dashboard(request):
    """Main dashboard view that shows different content based on user role"""
    user = request.user
    context = {}
    
    # Common data for all users
    user_requests = EventAccessRequest.objects.filter(user=user, status='PENDING')
    context['user_requests'] = user_requests
    
    template_name = 'users/dashboard.html'  # Default template

    if user.role == 'ORGANIZER':
        # Get organizer's events
        events = Event.objects.filter(organizer=user)
        
        # Calculate statistics
        total_participants = EventParticipant.objects.filter(event__organizer=user).count()
        total_photographers = EventCrew.objects.filter(event__organizer=user).count()
        
        # Get pending access requests
        pending_requests = EventAccessRequest.objects.filter(
            event__organizer=user,
            status='PENDING'
        )
        
        # Calculate total photos across all organizer's events
        total_photos = EventPhoto.objects.filter(event__organizer=user).count()
        
        # Get year-over-year event analytics
        current_year = timezone.now().year
        previous_year = current_year - 1
        
        # Get events by year
        current_year_events = events.filter(start_date__year=current_year).count()
        previous_year_events = events.filter(start_date__year=previous_year).count()
        
        # Calculate event growth percentage
        event_growth_percentage = 0
        if previous_year_events > 0:
            event_growth_percentage = int((current_year_events - previous_year_events) / previous_year_events * 100)
        
        # Get available years for dropdown
        available_years = events.dates('start_date', 'year').order_by('-start_date__year')
        available_years = [date.year for date in available_years]
        
        # Calculate photo growth
        current_year_photos = EventPhoto.objects.filter(
            event__organizer=user,
            upload_date__year=current_year
        ).count()
        
        previous_year_photos = EventPhoto.objects.filter(
            event__organizer=user,
            upload_date__year=previous_year
        ).count()
        
        photo_growth = 0
        if previous_year_photos > 0:
            photo_growth = int((current_year_photos - previous_year_photos) / previous_year_photos * 100)
        
        # Get monthly event data for chart
        monthly_event_data = []
        for month in range(1, 13):
            count = events.filter(
                start_date__year=current_year,
                start_date__month=month
            ).count()
            monthly_event_data.append(count)
            
        # Get monthly photo data for chart
        monthly_photo_data = []
        for month in range(1, 13):
            count = EventPhoto.objects.filter(
                event__organizer=user,
                upload_date__year=current_year,
                upload_date__month=month
            ).count()
            monthly_photo_data.append(count)
            
        # Calculate popular event types
        event_types = {}
        for event in events:
            event_type = event.get_event_type_display()
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
        # Sort event types by count
        sorted_event_types = sorted(event_types.items(), key=lambda x: x[1], reverse=True)
        top_event_types = sorted_event_types[:5]  # Get top 5 event types
        
        # Calculate upcoming events
        upcoming_events = events.filter(
            start_date__gt=timezone.now()
        ).order_by('start_date')[:5]  # Get 5 nearest upcoming events
        
        # Calculate popular events (by participant count)
        popular_events = []
        for event in events:
            participant_count = event.participants.count()
            popular_events.append({
                'event': event,
                'participant_count': participant_count
            })
        
        popular_events = sorted(popular_events, key=lambda x: x['participant_count'], reverse=True)[:5]
        
        context.update({
            'events': events,
            'total_participants': total_participants,
            'total_photographers': total_photographers,
            'pending_requests': pending_requests,
            'total_photos': total_photos,
            'current_year': current_year,
            'previous_year': previous_year,
            'current_year_events': current_year_events,
            'previous_year_events': previous_year_events,
            'event_growth_percentage': event_growth_percentage,
            'available_years': available_years,
            'photo_growth': photo_growth,
            'monthly_event_data': monthly_event_data,
            'monthly_photo_data': monthly_photo_data,
            'top_event_types': top_event_types,
            'upcoming_events': upcoming_events,
            'popular_events': popular_events,
        })
        template_name = 'users/dashboard_organizer.html'
        
    elif user.role == 'PHOTOGRAPHER':
        # Get photographer's event assignments
        crew_memberships = EventCrew.objects.filter(member=user)
        
        # to calculate monthly photo data
        monthly_photo_data = []
        current_year = timezone.now().year

        # Get monthly counts for the current year
        for month in range(1, 13):
            count = EventPhoto.objects.filter(
                uploaded_by=user,
                upload_date__year=current_year,
                upload_date__month=month
            ).count()
            monthly_photo_data.append(count)

        # Calculate statistics
        total_photos = EventPhoto.objects.filter(uploaded_by=user).count()
        upcoming_events = crew_memberships.filter(
            event__start_date__gt=timezone.now()
        ).count()
        
        # Calculate monthly photos
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_photos = EventPhoto.objects.filter(
            uploaded_by=user,
            upload_date__month=current_month,
            upload_date__year=current_year
        ).count()
        
        # Calculate yearly photos
        yearly_photos = EventPhoto.objects.filter(
            uploaded_by=user,
            upload_date__year=current_year
        ).count()
        
        # Calculate last year's photos for comparison
        last_year_photos = EventPhoto.objects.filter(
            uploaded_by=user,
            upload_date__year=current_year-1
        ).count()
        
        # Calculate growth percentage
        growth_percentage = 0
        if last_year_photos > 0:
            growth_percentage = int((yearly_photos - last_year_photos) / last_year_photos * 100)
        
        # Get total events the photographer has worked on
        total_events = EventCrew.objects.filter(member=user).values('event').distinct().count()
        
        context.update({
            'crew_memberships': crew_memberships,
            'total_photos': total_photos,
            'upcoming_events': upcoming_events,
            'monthly_photos': monthly_photos,
            'yearly_photos': yearly_photos,
            'last_year_photos': last_year_photos,
            'growth_percentage': growth_percentage,
            'total_events': total_events,
            'monthly_photo_data': monthly_photo_data,
        })
        template_name = 'users/dashboard_photographer.html'
        
    elif user.role == 'PARTICIPANT':
        # Get events the participant is part of
        participations = EventParticipant.objects.filter(user=user)
        
        # Calculate statistics
        photos_of_user = 0  # You'll need to implement photo tracking
        
        context.update({
            'participations': participations,
            'photos_of_user': photos_of_user,
        })
        template_name = 'users/dashboard_participant.html'
    
    return render(request, template_name, context)


@login_required
@csrf_exempt
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been successfully deleted.")
        logout(request)
        return redirect("home:index") 

    return render(request, "users/profile.html")


@login_required
def connections(request):
    """View for managing social and application connections"""
    user = request.user
    
    # Get existing connections
    social_connections = user.social_connections.all()
    
    # Create a dictionary for quick lookup
    connected_platforms = {conn.platform: conn for conn in social_connections}
    
    # Process connection actions
    if request.method == 'POST':
        action = request.POST.get('action')
        platform = request.POST.get('platform')
        
        if action == 'connect':
            form = SocialConnectionForm(request.POST)
            if form.is_valid():
                # Check if connection exists
                connection, created = SocialConnection.objects.get_or_create(
                    user=user,
                    platform=platform,
                    defaults={
                        'is_connected': True
                    }
                )
                
                # Update connection data
                connection.username = form.cleaned_data['username']
                connection.profile_url = form.cleaned_data['profile_url']
                connection.is_connected = True
                connection.save()
                
                messages.success(request, f"Successfully connected to {connection.get_platform_display()}")
                return redirect('users:connections')
            else:
                messages.error(request, "Please correct the errors below.")
                # Pass error back to the template with the specific platform modal open
                return redirect(f"{reverse('users:connections')}?show_modal={platform}")
                
        elif action == 'disconnect':
            if platform in connected_platforms:
                connected_platforms[platform].delete()
                messages.success(request, f"Successfully disconnected from {SocialConnection.PlatformTypes(platform).label}")
            else:
                messages.error(request, "Connection not found")
    
    # Group connections by type
    app_connections = ['GOOGLE', 'SLACK', 'GITHUB', 'MAILCHIMP', 'ASANA']
    social_media = ['FACEBOOK', 'TWITTER', 'INSTAGRAM', 'DRIBBBLE', 'BEHANCE']
    
    app_connection_data = []
    for platform in app_connections:
        is_connected = platform in connected_platforms
        
        if platform in connected_platforms:
            form = SocialConnectionForm(instance=connected_platforms[platform])
        else:
            form = SocialConnectionForm()
            
        app_connection_data.append({
            'platform': platform,
            'label': SocialConnection.PlatformTypes(platform).label,
            'is_connected': is_connected,
            'connection': connected_platforms.get(platform, None),
            'oauth_required': False,  # Changed to False for all platforms
            'form': form
        })
    
    social_media_data = []
    for platform in social_media:
        is_connected = platform in connected_platforms
        
        if platform in connected_platforms:
            form = SocialConnectionForm(instance=connected_platforms[platform])
        else:
            form = SocialConnectionForm()
        
        social_media_data.append({
            'platform': platform,
            'label': SocialConnection.PlatformTypes(platform).label,
            'is_connected': is_connected,
            'connection': connected_platforms.get(platform, None),
            'oauth_required': False,  # Changed to False for all platforms
            'form': form
        })
    
    context = {
        'app_connections': app_connection_data,
        'social_media': social_media_data,
    }
    
    return render(request, 'users/connections.html', context)