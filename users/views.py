# users/views.py
from datetime import timezone
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone


from photos.models import EventPhoto
from events.models import Event, EventAccessRequest, EventCrew, EventParticipant

from .forms import BasicRegistrationForm, OrganizerProfileForm, ParticipantProfileForm, PhotographerProfileForm

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


from django.contrib import messages

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


import base64
import io
import logging
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

logger = logging.getLogger(__name__)

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
        # Log form data for debugging (exclude image data for brevity)
        post_data = {k: v for k, v in request.POST.items() if k != 'avatar_data'}
        logger.debug(f"Form POST data: {post_data}")
        logger.debug(f"Files: {request.FILES}")
        
        # Create form without saving it yet
        form = FormClass(request.POST, request.FILES, instance=user)
        
        # Manually handle the cropped image
        if 'avatar_data' in request.POST and request.POST['avatar_data']:
            try:
                # Get the base64 string from the hidden input
                avatar_data = request.POST['avatar_data']
                
                # Remove the data URL prefix
                if ',' in avatar_data:
                    format_info, avatar_data = avatar_data.split(',', 1)
                    logger.debug(f"Image format info: {format_info}")
                
                # Decode base64 data
                avatar_image = base64.b64decode(avatar_data)
                
                # Create a Django file-like object
                avatar_file = ContentFile(avatar_image, name='profile-image.jpg')
                
                # Assign the file to the form instance
                form.instance.avatar = avatar_file
                logger.debug("Successfully processed avatar image")
            except Exception as e:
                logger.error(f"Error processing avatar: {str(e)}")
                messages.error(request, f"Error processing profile image: {str(e)}")
        
        # Check form validity and display errors
        if form.is_valid():
            logger.debug("Form is valid, saving...")
            form.save()
            messages.success(request, 'Profile completed successfully!')
            return redirect('users:dashboard')
        else:
            logger.error(f"Form validation errors: {form.errors}")
            messages.error(request, f"Please correct the errors below: {form.errors}")
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
        
        context.update({
            'events': events,
            'total_participants': total_participants,
            'total_photographers': total_photographers,
            'pending_requests': pending_requests,
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
def update_privacy(request):
    """Update user privacy settings"""
    if request.method == 'POST':
        user = request.user
        
        # Update privacy settings
        user.blur_requested = 'blur_requested' in request.POST
        user.remove_requested = 'remove_requested' in request.POST
        user.image_visibility = request.POST.get('image_visibility', 'PRIVATE')
        user.save()
        
        messages.success(request, 'Privacy settings updated successfully!')
    
    return redirect('users:dashboard')




from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def delete_account(request):
    if request.method == "POST":
        user = request.user
        user.delete()
        messages.success(request, "Your account has been successfully deleted.")
        logout(request)
        return redirect("home:landing") 

    return render(request, "users/profile.html")
