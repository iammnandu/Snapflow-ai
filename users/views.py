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

    return render(request, 'users/auth-register-basic.html', {'form': form})


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
        form = FormClass(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed successfully!')
            return redirect('users:profile')
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


# users/views.py (Add these functions)

@login_required
def dashboard(request):
    """Main dashboard view that shows different content based on user role"""
    user = request.user
    context = {}
    
    # Common data for all users
    user_requests = EventAccessRequest.objects.filter(user=user)
    context['user_requests'] = user_requests
    

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
        
    elif user.role == 'PHOTOGRAPHER':
        # Get photographer's event assignments
        crew_memberships = EventCrew.objects.filter(member=user)
        
        # Calculate statistics
        total_photos = 0  # Implement photo tracking later
        upcoming_events = crew_memberships.filter(
            event__start_date__gt=timezone.now()
        ).count()
        
        context.update({
            'crew_memberships': crew_memberships,
            'total_photos': total_photos,
            'upcoming_events': upcoming_events,
        })
        
    elif user.role == 'PARTICIPANT':
        # Get events the participant is part of
        participations = EventParticipant.objects.filter(user=user)
        
        # Calculate statistics
        photos_of_user = 0  # You'll need to implement photo tracking
        
        context.update({
            'participations': participations,
            'photos_of_user': photos_of_user,
        })
    
    return render(request, 'users/dashboard.html', context)


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