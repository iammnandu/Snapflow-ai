#events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse


from .models import (
    Event, EventAccessRequest, EventCrew, EventParticipant, EventConfiguration,
    EventTheme
)
from .forms import (
    EventAccessRequestForm, EventCreationForm, EventConfigurationForm, CrewInvitationForm,
    ParticipantInvitationForm, EventThemeForm, PrivacySettingsForm
)

# Event Creation and Management Views
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
        setup_step = self.kwargs.get('step', 'basic')
        form_classes = {
            'basic': EventCreationForm,
            'privacy': PrivacySettingsForm,
            'crew': CrewInvitationForm,
            'theme': EventThemeForm,
            'config': EventConfigurationForm,
        }
        return form_classes.get(setup_step)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = self.kwargs.get('step', 'basic')
        context['steps'] = ['basic', 'privacy', 'crew', 'theme', 'config']
        return context

from django.db.models import Sum

class EventDashboardView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = 'events/event_dashboard.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()  # Get the event instance

        # Annotate photos with total views and likes
        photos = event.photos.annotate(
            total_views=Sum('view_count'),
            total_likes=Sum('like_count') 
        )

        context.update({
            'crew_members': event.crew_members.all(),
            'participants': event.participants.all(),
            'is_organizer': event.organizer == self.request.user,
            'is_crew': event.crew_members.filter(member=self.request.user).exists(),
            'photos': photos  # Include the annotated photos
        })
        return context

from django.http import HttpResponseForbidden

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
    
    
# views.py
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.urls import reverse

class CrewManagementView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Event
    template_name = 'events/crew_management.html'
    context_object_name = 'event'
    
    def test_func(self):
        return self.get_object().organizer == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crew_form'] = CrewInvitationForm()
        context['crew_members'] = self.object.crew_members.all()
        return context
    
    def post(self, request, *args, **kwargs):
        event = self.get_object()
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
        
        # If form is invalid, return to the page with errors
        context = self.get_context_data()
        context['crew_form'] = form
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


# Equipment Configuration View
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

# Event Access Views
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
        return redirect('events:event_gallery', slug=slug)
    return render(request, 'events/create_temp_profile.html', {'event': event})

# AI Feature Management
@login_required
def toggle_ai_features(request, slug):
    event = get_object_or_404(Event, slug=slug, organizer=request.user)
    feature = request.POST.get('feature')
    enabled = request.POST.get('enabled') == 'true'
    
    if feature in ['face_detection', 'moment_detection', 'auto_tagging']:
        setattr(event, f'enable_{feature}', enabled)
        event.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

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

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.db.models import F
import json

@login_required
@require_http_methods(["POST"])
def handle_access_request(request, request_id):
    try:
        # Get the access request and verify permissions
        access_request = get_object_or_404(
            EventAccessRequest,
            id=request_id
        )
        
        # Check if the user is the event organizer
        if access_request.event.organizer != request.user:
            raise PermissionDenied("You don't have permission to handle this request")
        
        # Parse the action from JSON data
        data = json.loads(request.body)
        action = data.get('action')
        
        if action not in ['approve', 'reject']:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid action'
            }, status=400)
        
        # Handle approve action
        if action == 'approve':
            access_request.status = EventAccessRequest.RequestStatus.APPROVED
            
            # Add user to event based on their role
            if access_request.request_type == 'PHOTOGRAPHER':
                EventCrew.objects.create(
                    event=access_request.event,
                    member=access_request.user,
                    role='SECOND',
                    is_confirmed=True
                )
            else:
                EventParticipant.objects.create(
                    event=access_request.event,
                    user=access_request.user,
                    email=access_request.user.email,
                    name=access_request.user.get_full_name(),
                    participant_type='GUEST'
                )
        
        # Handle reject action
        elif action == 'reject':
            access_request.status = EventAccessRequest.RequestStatus.REJECTED
        
        # Save the changes
        access_request.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Request {action}ed successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except PermissionDenied as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=403)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An unexpected error occurred'
        }, status=500)

# events/views.py (Add or update this view)

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
                return redirect('events:event_gallery', slug=event.slug)
            
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



def access_requests(request):
    access_requests = EventAccessRequest.objects.filter(
        event__organizer=request.user
    ).select_related('user', 'event').order_by('-created_at')
    
    return render(request, 'events/request_list.html', {
        'access_requests': access_requests
    })



@login_required
def access_requests_list(request):
    # Get all requests for events organized by the user
    access_requests = EventAccessRequest.objects.filter(
        event__organizer=request.user
    ).select_related('user', 'event').order_by('-created_at')
    
    return render(request, 'events/request_list.html', {
        'access_requests': access_requests,
        'page_title': 'Access Requests'
    })

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
        else:
            EventParticipant.objects.create(
                event=access_request.event,
                user=access_request.user,
                email=access_request.user.email,
                name=access_request.user.get_full_name(),
                participant_type='GUEST'
            )
        
        access_request.save()
        messages.success(request, 'Request approved successfully')
        
    except Exception as e:
        messages.error(request, 'An error occurred while processing the request')
    
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

from django.views.generic.edit import UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages

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
    


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, View
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Event, EventPhoto, PhotoLike, PhotoComment

class EventGalleryView(DetailView):
    model = Event
    template_name = 'events/gallery.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.get_object()
        
        # Get photos with pagination
        photos = event.photos.all().order_by('-upload_date')
        paginator = Paginator(photos, 12)  # Show 12 photos per page
        page = self.request.GET.get('page')
        photos = paginator.get_page(page)
        
        # Check user permissions
        can_upload = False
        if self.request.user.is_authenticated:
            can_upload = (
                event.organizer == self.request.user or 
                event.crew_members.filter(member=self.request.user).exists() or 
                event.allow_guest_upload
            )
        
        context.update({
            'photos': photos,
            'can_upload': can_upload,
            'can_download': event.configuration.enable_download,
            'enable_comments': event.configuration.enable_comments,
            'enable_likes': event.configuration.enable_likes,
        })
        return context

class UploadPhotosView(LoginRequiredMixin, View):
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        
        # Check permissions
        if not (event.organizer == request.user or 
                event.crew_members.filter(member=request.user).exists() or 
                event.allow_guest_upload):
            messages.error(request, "You don't have permission to upload photos.")
            return redirect('events:event_gallery', slug=slug)
        
        images = request.FILES.getlist('images')
        
        # Validate files
        for image in images:
            # Check file size
            if image.size > event.configuration.max_upload_size:
                messages.error(request, f"File {image.name} is too large.")
                continue
                
            # Check file extension
            ext = image.name.split('.')[-1].lower()
            if ext not in event.configuration.allowed_formats.split(','):
                messages.error(request, f"File {image.name} has an invalid format.")
                continue
            
            # Create photo
            photo = EventPhoto.objects.create(
                event=event,
                image=image,
                uploaded_by=request.user
            )
        
        messages.success(request, f"{len(images)} photos uploaded successfully.")
        return redirect('events:event_gallery', slug=slug)


@login_required
def photo_comments(request, pk):
    photo = get_object_or_404(EventPhoto, pk=pk)
    comments = photo.comments.all()[:10]  # Fetch the 10 most recent comments
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'comment': comment.comment,
            'user_name': comment.user.get_full_name() or comment.user.username,
            'user_initials': comment.user.get_initials() if hasattr(comment.user, 'get_initials') else '',
            'profile_picture': comment.user.profile_picture.url if hasattr(comment.user, 'profile_picture') and comment.user.profile_picture else None,
            'created_at': comment.created_at.strftime('%m/%d/%Y %H:%M'),
            'can_delete': request.user == comment.user or request.user == photo.event.organizer
        })
    
    return JsonResponse({
        'status': 'success',
        'comments': comments_data
    })


class PhotoDetailView(DetailView):
    model = EventPhoto
    template_name = 'events/photo_detail.html'
    context_object_name = 'photo'
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo = self.get_object()
        context['event'] = photo.event
        # Increment view count
        photo.view_count += 1
        photo.save()
        
        context['can_download'] = photo.event.configuration.enable_download
        
        # Check if user has liked the photo
        if self.request.user.is_authenticated:
            context['user_liked'] = PhotoLike.objects.filter(
                photo=photo, user=self.request.user
            ).exists()
        
        return context

class PhotoActionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(EventPhoto, pk=pk)
        action = request.POST.get('action')
        
        if action == 'like':
            # Check if user has already liked the photo
            like = PhotoLike.objects.filter(photo=photo, user=request.user).first()
            
            if like:
                # Unlike the photo
                like.delete()
                photo.like_count = F('like_count') - 1
                photo.save()
                liked = False
            else:
                # Like the photo
                PhotoLike.objects.create(photo=photo, user=request.user)
                photo.like_count = F('like_count') + 1
                photo.save()
                liked = True
            
            # Refresh from db to get the updated like count
            photo.refresh_from_db()
            
            return JsonResponse({
                'status': 'success',
                'like_count': photo.like_count,
                'liked': liked
            })
            
        elif action == 'comment':
            comment = request.POST.get('comment')
            if comment:
                PhotoComment.objects.create(
                    photo=photo,
                    user=request.user,
                    comment=comment
                )
                return JsonResponse({
                    'status': 'success',
                    'message': 'Comment added successfully'
                })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid action'
        })

class DeletePhotoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(EventPhoto, pk=pk)
        event = photo.event
        
        # Check permissions
        if not (event.organizer == request.user or 
                event.crew_members.filter(member=request.user, role='LEAD').exists()):
            messages.error(request, "You don't have permission to delete photos.")
            return redirect('events:event_gallery', slug=event.slug)
        
        photo.delete()
        messages.success(request, "Photo deleted successfully.")
        return redirect('events:event_gallery', slug=event.slug)
    


from django.core.exceptions import PermissionDenied

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




# Additional view classes for events/views.py

from django.views.generic import FormView, View
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.crypto import get_random_string

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