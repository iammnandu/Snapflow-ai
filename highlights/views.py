from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from events.models import Event
from .models import BestShot, DuplicateGroup, DuplicatePhoto

@login_required
def event_highlights(request, event_slug):
    """View for displaying event highlights (best shots)."""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if user has access to this event
    if not (request.user == event.organizer or 
            event.eventcrew_set.filter(member=request.user).exists() or
            event.eventparticipant_set.filter(user=request.user).exists() or
            event.is_public):
        messages.error(request, "You don't have access to this event.")
        return redirect('events:dashboard')
    
    # Get best shots by category
    best_shots = {}
    for category in ['OVERALL', 'PORTRAIT', 'GROUP', 'ACTION', 'COMPOSITION', 'LIGHTING']:
        category_shots = BestShot.objects.filter(event=event, category=category)
        if category_shots.exists():
            best_shots[category] = category_shots
    
    context = {
        'event': event,
        'best_shots': best_shots,
    }
    
    return render(request, 'highlights/event_highlights.html', context)


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, DuplicateGroup

@login_required
def duplicate_photos(request, event_slug):
    """View for displaying duplicate photo groups for an event."""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if user is organizer or crew
    if not (request.user == event.organizer or 
            event.eventcrew_set.filter(member=request.user).exists()):
        messages.error(request, "Only organizers and crew members can manage duplicate photos.")
        return redirect('events:dashboard')
    
    # Get duplicate groups
    duplicate_groups = DuplicateGroup.objects.filter(event=event).prefetch_related("photos")

    # Assign primary photo for each group
    for group in duplicate_groups:
        group.primary_photo = group.photos.filter(is_primary=True).first()

    context = {
        'event': event,
        'duplicate_groups': duplicate_groups,
    }
    
    return render(request, 'highlights/duplicate_photos.html', context)


@login_required
def duplicate_group_detail(request, group_id):
    """View for displaying details of a duplicate photo group."""
    group = get_object_or_404(DuplicateGroup, id=group_id)
    event = group.event
    
    # Check if user is organizer or crew
    if not (request.user == event.organizer or 
            event.eventcrew_set.filter(member=request.user).exists()):
        messages.error(request, "Only organizers and crew members can manage duplicate photos.")
        return redirect('events:dashboard')
    
    # Get photos in this group
    duplicate_photos = group.photos.all().select_related('photo')
    
    context = {
        'event': event,
        'group': group,
        'duplicate_photos': duplicate_photos,
    }
    
    return render(request, 'highlights/duplicate_group_detail.html', context)


@login_required
def select_primary_photo(request, group_id, photo_id):
    """Set a photo as the primary (best) in a duplicate group."""
    group = get_object_or_404(DuplicateGroup, id=group_id)
    event = group.event
    
    # Check if user is organizer or crew
    if not (request.user == event.organizer or 
            event.eventcrew_set.filter(member=request.user).exists()):
        messages.error(request, "Only organizers and crew members can manage duplicate photos.")
        return redirect('events:dashboard')
    
    # Get the photo
    duplicate_photo = get_object_or_404(DuplicatePhoto, group=group, photo_id=photo_id)
    
    with transaction.atomic():
        # Reset all photos in group to non-primary
        group.photos.update(is_primary=False)
        
        # Set the selected photo as primary
        duplicate_photo.is_primary = True
        duplicate_photo.save()
    
    messages.success(request, "Primary photo updated successfully.")
    return redirect('highlights:duplicate_group_detail', group_id=group_id)