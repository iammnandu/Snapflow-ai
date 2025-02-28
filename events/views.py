import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.db.models import Q, Sum
from django.http import Http404, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, FormView, View
)
from django.views.generic.edit import UpdateView

from .models import (
    Event, EventAccessRequest, EventCrew, EventParticipant, EventConfiguration, EventTheme
)
from .forms import (
    EventAccessRequestForm, EventCreationForm, EventConfigurationForm, CrewInvitationForm,
    ParticipantInvitationForm, EventThemeForm, PrivacySettingsForm
)


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventCreationForm
    template_name = 'events/event_create.html'
    
    def form_valid(self, form):
        if self.request.user.role != 'ORGANIZER':
            messages.error(self.request, 'Only organizers can create events.')
            return redirect('events:event_list')
        else:
            form.instance.organizer = self.request.user
            form.instance.status = Event.EventStatus.DRAFT
            response = super().form_valid(form)
            
            # Create default configuration
            EventConfiguration.objects.create(event=self.object)
            messages.success(self.request, 'Event created successfully! Complete the setup process.')
            return response

class EventSetupView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    template_name = 'events/event_setup.html'
    context_object_name = 'event'

    def test_func(self):
        return self.get_object().organizer == self.request.user

    def get_form_class(self):
        setup_step = self.kwargs.get('step', 'privacy')
        form_classes = {
            'privacy': PrivacySettingsForm,
            'theme': EventThemeForm,
            'config': EventConfigurationForm,
        }
        return form_classes.get(setup_step)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        setup_step = self.kwargs.get('step', 'privacy')

        if setup_step in ['privacy', 'config']:
            event = self.get_object()
            config, created = EventConfiguration.objects.get_or_create(event=event)
            kwargs['instance'] = config

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        steps = ['privacy', 'theme', 'config']
        current_step = self.kwargs.get('step', 'privacy')

        if current_step not in steps:
            current_step = 'privacy'

        current_index = steps.index(current_step)
        previous_step = steps[current_index - 1] if current_index > 0 else None
        next_step = steps[current_index + 1] if current_index < len(steps) - 1 else None

        context.update({
            'current_step': current_step,
            'steps': steps,
            'previous_step': previous_step,
            'next_step': next_step
        })
        return context

    def form_valid(self, form):
        setup_step = self.kwargs.get('step', 'privacy')
        event = self.get_object()

        if setup_step in ['privacy', 'config']:
            config = form.save(commit=False)
            config.event = event
            config.save()
        elif setup_step == 'theme':
            form.save()

        steps = ['privacy', 'theme', 'config']
        current_index = steps.index(setup_step)

        if current_index < len(steps) - 1:
            next_step = steps[current_index + 1]
            return redirect('events:event_setup', slug=event.slug, step=next_step)
        else:
            return redirect('events:event_detail', slug=event.slug)

    def get_success_url(self):
        event = self.get_object()
        steps = ['privacy', 'theme', 'config']
        current_step = self.kwargs.get('step', 'privacy')

        if current_step not in steps:
            current_step = 'privacy'

        current_index = steps.index(current_step)

        if current_index < len(steps) - 1:
            next_step = steps[current_index + 1]
            return reverse('events:event_setup', kwargs={'slug': event.slug, 'step': next_step})
        else:
            return reverse('events:event_detail', kwargs={'slug': event.slug})


from django.shortcuts import render
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum

class EventDashboardView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_dashboard.html'
    context_object_name = 'event'

    def get_template_names(self):
        """Dynamically choose the template based on user role."""
        event = self.get_object()
        
        # Check if the current user is a participant in EventParticipant model
        is_participant = event.participants.filter(user=self.request.user).exists()
        
        if is_participant:
            return ['events/event_dashboard_participant.html']
        return ['events/event_dashboard.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()  # Get the event instance

        # Annotate photos with total views and likes
        photos = event.photos.annotate(
            total_views=Sum('view_count'),
            total_likes=Sum('like_count')
        )

        # Check if the user is in EventParticipant
        is_participant = event.participants.filter(user=self.request.user).exists()

        context.update({
            'crew_members': event.crew_members.all(),
            'participants': event.participants.all(),
            'is_organizer': event.organizer == self.request.user,
            'is_crew': event.crew_members.filter(member=self.request.user).exists(),
            'is_participant': is_participant,  # Pass participant status
            'photos': photos
        })
        return context


class EventParticipantsView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_participants.html'
    context_object_name = 'event'
    
    def get_object(self):
        return get_object_or_404(Event, slug=self.kwargs['slug'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        
        # Check if user is authorized to view participants
        is_organizer = event.organizer == self.request.user
        is_crew = event.crew_members.filter(member=self.request.user).exists()
        
        if not (is_organizer or is_crew):
            return HttpResponseForbidden("You don't have permission to view this page.")
        
        # Add user role to context
        context['is_organizer'] = is_organizer
        context['is_crew'] = is_crew
        
        # Get participants with filtering options
        participant_type = self.request.GET.get('type', None)
        
        participants = event.participants.all()
        if participant_type:
            participants = participants.filter(participant_type=participant_type)
        
        context['participants'] = participants
        
        # Get participant type choices for filter dropdown
        context['participant_types'] = EventParticipant.ParticipantTypes.choices
        if participant_type:
            display_name = dict(EventParticipant.ParticipantTypes.choices).get(participant_type, participant_type)
        else:
            display_name = None

        context['current_filter'] = display_name

        
        # Stats
        context['total_participants'] = event.participants.count()
        context['registered_count'] = event.participants.filter(is_registered=True).count()
        
        return context
    
    
class CrewManagementView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Event
    template_name = 'events/crew_management.html'
    context_object_name = 'event'
    
    def test_func(self):
        return self.get_object().organizer == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crew_form'] = CrewInvitationForm()
        context['crew_members'] = self.object.crew_members.all().select_related('member')
        return context
    
    def post(self, request, *args, **kwargs):
        event = self.get_object()
        action = request.POST.get('action', 'invite')
        
        if action == 'delete':
            # Handle crew member deletion
            crew_id = request.POST.get('crew_id')
            if crew_id:
                try:
                    crew_member = event.crew_members.get(id=crew_id)
                    username = crew_member.member.username
                    crew_member.delete()
                    messages.success(request, f'Crew member {username} has been removed successfully.')
                except CrewMember.DoesNotExist:
                    messages.error(request, 'Crew member not found.')
            return redirect('events:crew_management', slug=event.slug)
            
        elif action == 'invite':
            # Handle crew invitation (existing functionality)
            form = CrewInvitationForm(request.POST)
            
            if form.is_valid():
                # Create pending crew member
                crew = form.save(commit=False)
                crew.event = event
                crew.member = form.cleaned_data['user']  # Use the user we found in form validation
                crew.is_confirmed = False
                crew.save()
                
                # Generate invitation token
                signer = TimestampSigner()
                token = signer.sign(str(crew.id))
                
                # Generate invitation URL
                invite_url = request.build_absolute_uri(
                    reverse('events:accept_crew_invitation', kwargs={'token': token})
                )
                
                # Here you would typically send notification to the user
                # For now, we'll just add a message with the URL
                messages.success(
                    request, 
                    f'Invitation sent to {crew.member.username}. They can accept it at: {invite_url}'
                )
                
                return redirect('events:crew_management', slug=event.slug)
        
        # If form is invalid or action not recognized, return to the page with errors
        context = self.get_context_data()
        context['crew_form'] = form if action == 'invite' else CrewInvitationForm()
        return self.render_to_response(context)

def accept_crew_invitation(request, token):
    signer = TimestampSigner()
    try:
        # Verify token and get crew ID (valid for 7 days)
        crew_id = signer.unsign(token, max_age=604800)
        crew = get_object_or_404(EventCrew, id=crew_id, is_confirmed=False)
        
        # Verify the invitation is for the logged-in user
        if request.user != crew.member:
            messages.error(request, "This invitation is not for you.")
            return redirect('events:event_list')
        
        # Accept invitation
        crew.is_confirmed = True
        crew.save()
        
        messages.success(request, f"You have joined {crew.event.title} as {crew.get_role_display()}")
        return redirect('events:event_dashboard', slug=crew.event.slug)
        
    except (SignatureExpired, BadSignature):
        messages.error(request, "This invitation link is invalid or has expired.")
        return redirect('events:event_list')


class EquipmentConfigurationView(LoginRequiredMixin, UpdateView):
    model = EventCrew
    template_name = 'events/equipment_config.html'
    fields = ['equipment']
    context_object_name = 'crew'
   
    def get_object(self):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # Check if user is the organizer
        if event.organizer == self.request.user:
            # For organizers, we'll just display the page in read-only mode
            # We'll handle this in get() method
            self.is_organizer = True
            # Return any crew member just to have a valid object
            # (we'll override form handling for organizers)
            return EventCrew.objects.filter(event=event).first()
        else:
            # For crew members, return their specific record
            self.is_organizer = False
            return get_object_or_404(
                EventCrew,
                event=event,
                member=self.request.user
            )
   
    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            if self.object is None:
                messages.error(request, "No crew members found for this event.")
                return redirect('events:event_detail', slug=self.kwargs['slug'])
            
            context = self.get_context_data(object=self.object)
            
            # If user is organizer, make the form read-only
            if hasattr(self, 'is_organizer') and self.is_organizer:
                for field in context['form'].fields.values():
                    field.disabled = True
                
            return self.render_to_response(context)
        except Http404:
            messages.error(request, "You don't have permission to view this page.")
            return redirect('events:event_detail', slug=self.kwargs['slug'])
   
    def post(self, request, *args, **kwargs):
        # Get the event
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # If user is the organizer, they shouldn't be able to update
        if event.organizer == request.user:
            messages.warning(request, "As an organizer, you can only view equipment details.")
            return redirect('events:event_detail', slug=self.kwargs['slug'])
            
        return super().post(request, *args, **kwargs)
   
    def get_success_url(self):
        # Redirect back to the event detail page after successful update
        return reverse('events:event_detail', kwargs={'slug': self.kwargs['slug']})
   
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Equipment configuration updated!')
        return response
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # Add the event to the context for template use
        context['event'] = event
        
        # Check if user is organizer and add to context
        context['is_organizer'] = event.organizer == self.request.user
        
        # If user is organizer, get all crew members' equipment
        if context['is_organizer']:
            context['all_crew_equipment'] = EventCrew.objects.filter(
                event=event
            ).select_related('member')
        else:
            # Get any existing equipment configurations for this user
            context['existing_equipment'] = EventCrew.objects.filter(
                member=self.request.user
            ).exclude(
                pk=self.object.pk  # Exclude current one
            ).select_related('event')
            
        return context


@login_required
def create_temp_profile(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if request.method == 'POST':
        # Create temporary participant profile
        participant = EventParticipant.objects.create(
            event=event,
            user=request.user,
            email=request.user.email,
            name=request.user.get_full_name(),
            registration_code=get_random_string(20)
        )
        messages.success(request, 'Temporary profile created successfully!')
        return redirect('photos:event_gallery', slug=slug)
    return render(request, 'events/create_temp_profile.html', {'event': event})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # Temporarily disable CSRF for testing; remove later!
@login_required
def toggle_ai_features(request, slug):
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        feature = data.get('feature')
        enabled = data.get('enabled', False)

        event = get_object_or_404(Event, slug=slug, organizer=request.user)

        if feature in ['face_detection', 'moment_detection', 'auto_tagging']:
            setattr(event, f'enable_{feature}', enabled)
            event.save()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid feature'}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    
    def get_queryset(self):
        # This method will be used for pagination, we'll override get_context_data instead
        return Event.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get filter parameters
        event_type = self.request.GET.get('event_type', '')
        status = self.request.GET.get('status', '')
        
        # Base queryset with filters
        base_query = Event.objects.all()
        if event_type:
            base_query = base_query.filter(event_type=event_type)
        if status:
            base_query = base_query.filter(status=status)
        
        if user.is_authenticated:
            # Registered events: events the user is organizing, part of crew, or participating in
            registered_events = base_query.filter(
                Q(organizer=user) | 
                Q(crew_members__member=user) | 
                Q(participants__user=user)
            ).distinct()
            
            # Public events: events that are public but user is not related to
            public_events = base_query.filter(
                is_public=True
            ).exclude(
                Q(organizer=user) | 
                Q(crew_members__member=user) | 
                Q(participants__user=user)
            ).distinct()
        else:
            registered_events = Event.objects.none()
            public_events = base_query.filter(is_public=True)
        
        # Add to context
        context['registered_events'] = registered_events
        context['public_events'] = public_events
        context['event_types'] = Event.EventTypes.choices
        context['event_statuses'] = Event.EventStatus.choices
        context['selected_type'] = event_type
        context['selected_status'] = status
        context['total_events_count'] = registered_events.count() + public_events.count()
        
        return context

class RequestEventAccessView(LoginRequiredMixin, FormView):
    template_name = 'events/request_access.html'
    form_class = EventAccessRequestForm
    success_url = reverse_lazy('users:dashboard')

    def form_valid(self, form):
        event = form.cleaned_data['event']
        
        # Check if request already exists
        existing_request = EventAccessRequest.objects.filter(
            event=event,
            user=self.request.user
        ).first()
        
        if existing_request:
            messages.warning(self.request, 'You have already requested access to this event')
            return redirect('users:dashboard')

        # Create new request
        EventAccessRequest.objects.create(
            event=event,
            user=self.request.user,
            request_type='PHOTOGRAPHER' if self.request.user.role == 'PHOTOGRAPHER' else 'PARTICIPANT',
            message=form.cleaned_data.get('message', '')
        )
        
        messages.success(self.request, 'Access request sent successfully')
        return super().form_valid(form)


@login_required
def request_access(request):
    """Simple form to request access to an event using event code"""
    if request.method == 'POST':
        event_code = request.POST.get('event_code', '').upper()
        
        try:
            event = Event.objects.get(event_code=event_code)
            
            # Check if user already has access
            if event.organizer == request.user:
                messages.info(request, 'You are the organizer of this event.')
                return redirect('events:event_dashboard', slug=event.slug)
            
            if EventCrew.objects.filter(event=event, member=request.user).exists():
                messages.info(request, 'You are already a crew member for this event.')
                return redirect('events:event_dashboard', slug=event.slug)
                
            if EventParticipant.objects.filter(event=event, user=request.user).exists():
                messages.info(request, 'You are already a participant in this event.')
                return redirect('photos:event_gallery', slug=event.slug)
            
            # Check if request already exists
            if EventAccessRequest.objects.filter(event=event, user=request.user).exists():
                messages.warning(request, 'You have already requested access to this event.')
                return redirect('users:dashboard')
            
            # Create new request
            EventAccessRequest.objects.create(
                event=event,
                user=request.user,
                request_type='PHOTOGRAPHER' if request.user.role == 'PHOTOGRAPHER' else 'PARTICIPANT',
                message='Request via event code'
            )
            
            messages.success(request, f'Access request sent to "{event.title}" successfully!')
        except Event.DoesNotExist:
            messages.error(request, 'Invalid event code. Please check and try again.')
    
    return redirect('users:dashboard')

@login_required
def cancel_access_request(request, request_id):
    """
    View to cancel a user's own event access request
    """
    try:
        # Get the access request, ensuring it belongs to the current user
        access_request = EventAccessRequest.objects.get(
            id=request_id,
            user=request.user
        )
        
        # Only allow cancellation if the request is still pending
        if access_request.status == EventAccessRequest.RequestStatus.PENDING:
            # Store event info for the message
            event_name = access_request.event.name if hasattr(access_request.event, 'name') else "this event"
            request_type = access_request.get_request_type_display() if hasattr(access_request, 'get_request_type_display') else access_request.request_type
            
            # Delete the request
            access_request.delete()
            
            messages.success(
                request, 
                f"Your {request_type} request for {event_name} has been cancelled."
            )
        else:
            messages.error(
                request,
                "This request cannot be cancelled because it has already been processed."
            )
            
    except EventAccessRequest.DoesNotExist:
        messages.error(
            request,
            "The request you're trying to cancel does not exist or doesn't belong to you."
        )
    
    # Redirect back to the access requests list
    return redirect('events:access_requests')

@login_required
def access_requests_list(request):
    # First check if any of the events exist
    organized_events = Event.objects.filter(organizer=request.user).exists()
    
    # Get requests for events that definitely exist
    organized_requests = EventAccessRequest.objects.filter(
        event__organizer=request.user,
        event__isnull=False  # Ensure event exists
    ).select_related('user', 'event').order_by('-created_at')
    
    # Get user requests where the event definitely exists
    user_requests = EventAccessRequest.objects.filter(
        user=request.user,
        event__isnull=False  # Ensure event exists
    ).select_related('user', 'event').order_by('-created_at')
    
    # Separate photographer and participant requests
    photographer_requests = user_requests.filter(request_type='PHOTOGRAPHER')
    participant_requests = user_requests.filter(request_type='PARTICIPANT')
    
    # Determine user roles
    is_organizer = organized_events  # Using the direct event query result
    is_photographer = photographer_requests.exists()
    is_participant = participant_requests.exists()
    
    context = {
        'organized_requests': organized_requests,
        'photographer_requests': photographer_requests,
        'participant_requests': participant_requests,
        'is_organizer': is_organizer,
        'is_photographer': is_photographer,
        'is_participant': is_participant,
        'page_title': 'Access Requests'
    }
    
    return render(request, 'events/request_list.html', context)



@login_required
@require_http_methods(["POST"])
def approve_request(request, request_id):
    try:
        access_request = get_object_or_404(EventAccessRequest, id=request_id)
        
        # Check if the user is the event organizer
        if access_request.event.organizer != request.user:
            messages.error(request, "You don't have permission to handle this request")
            return redirect('events:access_requests')
        
        # Handle approve action
        access_request.status = EventAccessRequest.RequestStatus.APPROVED
        
        # Add user to event based on their role
        if access_request.request_type == 'PHOTOGRAPHER':
            EventCrew.objects.create(
                event=access_request.event,
                member=access_request.user,
                role='SECOND',
                is_confirmed=True
            )
        else:  # PARTICIPANT
            # Generate a unique registration code for the participant
            try:
                unique_code = EventParticipant.generate_unique_code()
                EventParticipant.objects.create(
                    event=access_request.event,
                    user=access_request.user,
                    email=access_request.user.email,
                    name=access_request.user.get_full_name() or access_request.user.username,
                    participant_type='GUEST',
                    registration_code=unique_code,
                    is_registrated=True
                )
            except Exception as participant_error:
                messages.error(request, f"Error adding participant: {participant_error}")
                return redirect('events:access_requests')
        
        access_request.save()
        messages.success(request, 'Request approved successfully')
        
    except Exception as e:
        messages.error(request, f'An error occurred while processing the request: {str(e)}')
    
    return redirect('events:access_requests')

@login_required
@require_http_methods(["POST"])
def reject_request(request, request_id):
    try:
        access_request = get_object_or_404(EventAccessRequest, id=request_id)
        
        # Check if the user is the event organizer
        if access_request.event.organizer != request.user:
            messages.error(request, "You don't have permission to handle this request")
            return redirect('events:access_requests')
        
        # Handle reject action
        access_request.status = EventAccessRequest.RequestStatus.REJECTED
        access_request.save()
        
        messages.success(request, 'Request rejected successfully')
        
    except Exception as e:
        messages.error(request, 'An error occurred while processing the request')
    
    return redirect('events:access_requests')



class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventCreationForm
    template_name = 'events/event_edit.html'
    
    def get_queryset(self):
        # Ensure users can only edit their own events
        return Event.objects.filter(organizer=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, 'Event updated successfully!')
        return reverse_lazy('events:event_dashboard', kwargs={'slug': self.object.slug})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        return response
    

def user_can_access_event(user, event):
    return (
        user.is_authenticated and (
            event.is_public or
            event.organizer == user or
            event.crew_members.filter(member=user).exists() or
            event.participants.filter(user=user, is_registered=True).exists()
        )
    )

def get_object(self, queryset=None):
    event = super().get_object(queryset)
    if not user_can_access_event(self.request.user, event):
        raise PermissionDenied
    return event

class AddParticipantView(LoginRequiredMixin, FormView):
    template_name = 'events/event_participants.html'  # Not used directly
    
    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # Check if user is authorized
        if event.organizer != request.user:
            return HttpResponseForbidden("You don't have permission to add participants.")
        
        # Get form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        participant_type = request.POST.get('participant_type')
        
        # Check if email already exists
        if EventParticipant.objects.filter(event=event, email=email).exists():
            messages.error(request, f"A participant with the email {email} already exists.")
            return HttpResponseRedirect(reverse('events:event_participants', kwargs={'slug': event.slug}))
        
        # Create registration code
        registration_code = get_random_string(20)
        
        # Create the participant
        participant = EventParticipant.objects.create(
            event=event,
            name=name,
            email=email,
            participant_type=participant_type,
            registration_code=registration_code
        )
        
        # TODO: Send invitation email
        
        messages.success(request, f"Participant {name} has been added successfully.")
        return HttpResponseRedirect(reverse('events:event_participants', kwargs={'slug': event.slug}))

class EditParticipantView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        participant = get_object_or_404(EventParticipant, pk=self.kwargs['participant_id'], event=event)
        
        # Check if user is authorized
        if event.organizer != request.user:
            return HttpResponseForbidden("You don't have permission to edit participants.")
        
        # Update participant details
        participant.name = request.POST.get('name')
        participant.email = request.POST.get('email')
        participant.participant_type = request.POST.get('participant_type')
        participant.save()
        
        messages.success(request, f"Participant {participant.name} has been updated successfully.")
        return HttpResponseRedirect(reverse('events:event_participants', kwargs={'slug': event.slug}))

class RemoveParticipantView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        participant = get_object_or_404(EventParticipant, pk=self.kwargs['participant_id'], event=event)
        
        # Check if user is authorized
        if event.organizer != request.user:
            return HttpResponseForbidden("You don't have permission to remove participants.")
        
        # Delete the participant
        participant_name = participant.name
        participant.delete()
        
        messages.success(request, f"Participant {participant_name} has been removed successfully.")
        return HttpResponseRedirect(reverse('events:event_participants', kwargs={'slug': event.slug}))

class ResendParticipantInviteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        participant = get_object_or_404(EventParticipant, pk=self.kwargs['participant_id'], event=event)
        
        # Check if user is authorized
        if event.organizer != request.user:
            return HttpResponseForbidden("You don't have permission to resend invitations.")
        
        # TODO: Resend invitation email
        
        messages.success(request, f"Invitation has been resent to {participant.name}.")
        return HttpResponseRedirect(reverse('events:event_participants', kwargs={'slug': event.slug}))