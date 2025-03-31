# highlights/views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import Event, DuplicateGroup
from events.models import Event
from .models import BestShot, DuplicateGroup, DuplicatePhoto

@login_required
def event_highlights(request, event_slug):
    """View for displaying event highlights (best shots)."""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if user has access to this event
    if not (request.user == event.organizer or 
            event.crew_members.filter(member=request.user).exists() or
            event.participants.filter(user=request.user).exists() or
            event.is_public):
        messages.error(request, "You don't have access to this event.")
        return redirect('events:dashboard')
    
    # Get best shots by category - separate good and problem categories
    good_shots = {}
    problem_shots = {}
    
    # Good categories
    for category in ['OVERALL', 'PORTRAIT', 'GROUP', 'ACTION', 'COMPOSITION', 'LIGHTING']:
        category_shots = BestShot.objects.filter(event=event, category=category).order_by('-score')
        if category_shots.exists():
            good_shots[category] = category_shots
    
    # Problem categories - for these, higher score means worse quality
    for category in ['BLURRY', 'UNDEREXPOSED', 'OVEREXPOSED', 'ACCIDENTAL']:
        category_shots = BestShot.objects.filter(event=event, category=category).order_by('-score')
        if category_shots.exists():
            problem_shots[category] = category_shots
    
    context = {
        'event': event,
        'good_shots': good_shots,
        'problem_shots': problem_shots,
    }
    
    return render(request, 'highlights/event_highlights.html', context)


@login_required
def duplicate_photos(request, event_slug):
    """View for displaying duplicate photo groups for an event."""
    event = get_object_or_404(Event, slug=event_slug)
    
    # Check if user is organizer or crew
    if not (request.user == event.organizer or 
            event.crew_members.filter(member=request.user).exists()):
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
            event.crew_members.filter(member=request.user).exists()):
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
            event.crew_members.filter(member=request.user).exists()):
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




@login_required
def delete_duplicate_photos(request, group_id):
    """Delete multiple photos from a duplicate group."""
    group = get_object_or_404(DuplicateGroup, id=group_id)
    event = group.event
    
    # Check if user is organizer or crew
    if not (request.user == event.organizer or 
            event.crew_members.filter(member=request.user).exists()):
        messages.error(request, "Only organizers and crew members can manage duplicate photos.")
        return redirect('events:dashboard')
    
    if request.method == 'POST':
        photo_ids = request.POST.getlist('photo_ids')
        
        if not photo_ids:
            messages.warning(request, "No photos were selected for deletion.")
            return redirect('highlights:duplicate_group_detail', group_id=group_id)
            
        with transaction.atomic():
            # Check if we're trying to delete the primary photo
            primary_photo = DuplicatePhoto.objects.filter(group=group, is_primary=True).first()
            
            if primary_photo and str(primary_photo.photo.id) in photo_ids:
                messages.error(request, "Cannot delete the primary photo. Please select a different primary photo first.")
                return redirect('highlights:duplicate_group_detail', group_id=group_id)
            
            # Delete the selected photos
            deleted_count = 0
            for photo_id in photo_ids:
                try:
                    dup_photo = DuplicatePhoto.objects.get(group=group, photo_id=photo_id)
                    # Option 1: Delete just the DuplicatePhoto entry
                    # dup_photo.delete()
                    
                    # Option 2: Delete both the DuplicatePhoto entry and the actual EventPhoto
                    photo = dup_photo.photo
                    dup_photo.delete()
                    photo.delete()  # This will also delete the image file
                    
                    deleted_count += 1
                except:
                    continue
            
            # If we deleted all photos except the primary, delete the group
            remaining = group.photos.count()
            if remaining <= 1:
                messages.info(request, f"Removed duplicate group as only the primary photo remains.")
                group.delete()
                return redirect('highlights:duplicate_photos', event_slug=event.slug)
            
            messages.success(request, f"Successfully deleted {deleted_count} duplicate photos.")
        
    return redirect('highlights:duplicate_group_detail', group_id=group_id)