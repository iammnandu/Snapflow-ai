# photos/views.py
import os
import io
import json
import zipfile
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST

from django.db.models import F, Q

from events.models import Event, EventParticipant
from .models import EventPhoto, PhotoLike, PhotoComment, UserPhotoMatch, UserGallery
from .tasks import *



class EventGalleryView(DetailView):
    model = Event
    template_name = 'photos/gallery.html'
    context_object_name = 'event'
   
    def get(self, request, *args, **kwargs):
        event = self.get_object()
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            messages.warning(request, "You must be logged in to view the gallery")
            return redirect('login')
            
        # Always allow access to organizers and crew members
        is_organizer = event.organizer == request.user
        is_crew = event.crew_members.filter(member=request.user).exists()
        
        if not (is_organizer or is_crew):
            # Check participant gallery access
            try:
                participant = event.participants.get(user=request.user)
                if participant.gallery_access in ['NOT_REQUESTED', 'PENDING', 'DENIED']:
                    # Redirect to event dashboard with appropriate message
                    if participant.gallery_access == 'NOT_REQUESTED':
                        messages.info(request, "You need to request access to view this gallery")
                    elif participant.gallery_access == 'PENDING':
                        messages.info(request, "Your gallery access request is pending")
                    else:  # DENIED
                        messages.error(request, "Your gallery access request has been denied")
                    return redirect('events:event_dashboard', slug=event.slug)
            except EventParticipant.DoesNotExist:
                messages.warning(request, "You are not a participant in this event")
                return redirect('events:event_list')
        
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        event = self.get_object()
       
        # Get tag filter
        tag_filter = self.request.GET.get('tag')
        photos_queryset = event.photos.all()
       
        # Apply tag filter if specified
        if tag_filter:

            photo_ids = []
            for photo in photos_queryset:
                if photo.scene_tags and tag_filter in photo.scene_tags:
                    photo_ids.append(photo.id)
            photos_queryset = photos_queryset.filter(id__in=photo_ids)
       
        # Apply sorting
        sort_by = self.request.GET.get('sort', 'recent')
        if sort_by == 'popular':
            photos_queryset = photos_queryset.order_by('-like_count', '-view_count', '-upload_date')
        elif sort_by == 'quality':
            photos_queryset = photos_queryset.order_by('-quality_score', '-upload_date')
        else:  # Default: recent
            photos_queryset = photos_queryset.order_by('-upload_date')
       
        # Get unique tags across all event photos
        all_tags = set()
        for photo in event.photos.exclude(scene_tags__isnull=True):
            if photo.scene_tags:
                all_tags.update(photo.scene_tags)
       
        # Get photos with pagination
        paginator = Paginator(photos_queryset, 12)  # Show 12 photos per page
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
            'available_tags': sorted(all_tags),
            'current_tag': tag_filter,
            'current_sort': sort_by,
        })


        # Add gallery access status to context
        if self.request.user.is_authenticated:
            try:
                participant = event.participants.get(user=self.request.user)
                context['gallery_access_status'] = participant.gallery_access
            except EventParticipant.DoesNotExist:
                context['gallery_access_status'] = None
        
        # Rest of existing context data code...
        return context

class UploadPhotosView(LoginRequiredMixin, View):
    def post(self, request, slug):
        event = get_object_or_404(Event, slug=slug)
        
        # Check permissions
        if not (event.organizer == request.user or 
                event.crew_members.filter(member=request.user).exists() or 
                event.allow_guest_upload):
            messages.error(request, "You don't have permission to upload photos.")
            return redirect('photos:event_gallery', slug=slug)
        
        images = request.FILES.getlist('images')
        uploaded_photos = []
        
        # Validate files
        for image in images:
            if image.size > event.configuration.max_upload_size:
                messages.error(request, f"File {image.name} is too large.")
                continue

            ext = image.name.split('.')[-1].lower()
            if ext not in event.configuration.allowed_formats.split(','):
                messages.error(request, f"File {image.name} has an invalid format.")
                continue

            photo = EventPhoto.objects.create(
                event=event,
                image=image,
                uploaded_by=request.user
            )
            uploaded_photos.append(photo)

        for photo in uploaded_photos:
            process_photo.delay(photo.id)
        
        messages.success(request, f"{len(uploaded_photos)} photos uploaded successfully and queued for AI processing.")
        return redirect('photos:event_gallery', slug=slug)


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
    template_name = 'photos/photo_detail.html'
    context_object_name = 'photo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo = self.get_object()
        context['event'] = photo.event

        photo.view_count += 1
        photo.save()
        
        context['can_download'] = photo.event.configuration.enable_download

        context['has_enhanced_version'] = photo.has_enhanced_version()
        context['scene_tags'] = photo.get_tags()
    
        recognized_users = []

        matches = UserPhotoMatch.objects.filter(photo=photo).select_related('user')
        
        for match in matches:
            recognized_users.append({
                'user': match.user,
                'confidence': match.confidence_score,
                'position': None 
            })
            

        if photo.detected_faces:
            for face_data in photo.detected_faces:
                if face_data.get('user_id'):
                    user_id = face_data.get('user_id')
                    # Find the corresponding match
                    for user_info in recognized_users:
                        if user_info['user'].id == user_id:
                            user_info['position'] = face_data.get('position')
                            break
        
        context['recognized_users'] = recognized_users
        
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

            like = PhotoLike.objects.filter(photo=photo, user=request.user).first()
            
            if like:

                like.delete()
                photo.like_count = F('like_count') - 1
                photo.save()
                liked = False
            else:

                PhotoLike.objects.create(photo=photo, user=request.user)
                photo.like_count = F('like_count') + 1
                photo.save()
                liked = True

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
                
        elif action == 'reprocess':
            
            if photo.event.organizer == request.user or photo.event.crew_members.filter(member=request.user).exists():

                photo.processed = False
                photo.save(update_fields=['processed'])
                process_photo.delay(photo.id)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Photo queued for reprocessing'
                })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid action'
        })

class DeletePhotoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        photo = get_object_or_404(EventPhoto, pk=pk)
        event = photo.event
        

        if not (event.organizer == request.user or 
                event.crew_members.filter(member=request.user, role='LEAD').exists()):
            messages.error(request, "You don't have permission to delete photos.")
            return redirect('photos:event_gallery', slug=event.slug)
        
        photo.delete()
        messages.success(request, "Photo deleted successfully.")
        return redirect('photos:event_gallery', slug=event.slug)



class UserGalleryView(LoginRequiredMixin, ListView):
    model = EventPhoto
    template_name = 'photos/user_gallery.html'
    context_object_name = 'photos'
    paginate_by = 12
    
    def get_queryset(self):
        # Get photos where the current user appears
        return EventPhoto.objects.filter(
            user_matches__user=self.request.user
        ).order_by('-upload_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's gallery or create it if it doesn't exist
        gallery, created = UserGallery.objects.get_or_create(user=self.request.user)
        
        # Get unique events where user appears in photos
        user_events = Event.objects.filter(
            photos__user_matches__user=self.request.user
        ).distinct()
        
        # Get filter parameters
        event_filter = self.request.GET.get('event')
        tag_filter = self.request.GET.get('tag')
        
        # Apply filters to base queryset
        filtered_queryset = self.get_queryset()
        
        if event_filter:
            filtered_queryset = filtered_queryset.filter(event_id=event_filter)
            
        if tag_filter:
            filtered_queryset = filtered_queryset.filter(scene_tags__contains=[tag_filter])
        
        # Get unique tags across all user photos
        all_tags = set()
        for photo in self.get_queryset().exclude(scene_tags__isnull=True):
            if photo.scene_tags:
                all_tags.update(photo.scene_tags)
        
        # Apply pagination to filtered queryset
        paginator = Paginator(filtered_queryset, self.paginate_by)
        page = self.request.GET.get('page')
        photos = paginator.get_page(page)
        
        context.update({
            'gallery': gallery,
            'photos': photos,
            'user_events': user_events,
            'available_tags': sorted(all_tags),
            'current_event': event_filter,
            'current_tag': tag_filter,
        })
        
        return context
    


@login_required
def reanalyze_faces(request, pk):
    photo = get_object_or_404(EventPhoto, pk=pk)
    
    # Check permissions
    if not (photo.event.organizer == request.user or 
            photo.event.crew_members.filter(member=request.user).exists()):
        messages.error(request, "You don't have permission to reanalyze photos.")
        return redirect('photos:photo_detail', pk=pk)
    
    # Clear existing face matches
    UserPhotoMatch.objects.filter(photo=photo).delete()
    
    # Reset face detection data
    photo.detected_faces = []
    photo.save(update_fields=['detected_faces'])
    
    # Queue for reprocessing
    process_photo.delay(photo.id)
    
    messages.success(request, "Photo queued for face reanalysis.")
    return redirect('photos:photo_detail', pk=pk)


@login_required
@require_POST
def download_photos(request, slug):
    event = get_object_or_404(Event, slug=slug)
    
    # Check if user has permission to download photos
    if not event.configuration.enable_download:
        messages.error(request, "Downloads are not enabled for this event.")
        return redirect('photos:event_gallery', slug=slug)
    
    # Get photo IDs from form data
    photo_ids_str = request.POST.get('photo_ids', '')
    if not photo_ids_str:
        messages.error(request, "No photos selected for download.")
        return redirect('photos:event_gallery', slug=slug)
    
    photo_ids = photo_ids_str.split(',')
    download_type = request.POST.get('download_type', 'zip')
    
    # Get the photos
    photos = EventPhoto.objects.filter(id__in=photo_ids, event=event)
    
    if not photos.exists():
        messages.error(request, "No valid photos found to download.")
        return redirect('photos:event_gallery', slug=slug)
    
    # If only one photo and download_type is 'single', download it directly
    if download_type == 'single' and photos.count() == 1:
        photo = photos.first()
        file_path = photo.image.path
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Get the file extension
            file_name = os.path.basename(file_path)
            
            response = HttpResponse(file_data, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
    
    # For multiple photos or if download_type is 'zip', create a zip file
    zip_buffer = BytesIO()
    event_name = event.slug
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for photo in photos:
            file_path = photo.image.path
            
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    zip_file.writestr(file_name, f.read())
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{event_name}_photos.zip"'
    
    return response


class DownloadPhotosView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # Get the photo IDs from the form
        photo_ids_str = request.POST.get('photo_ids', '')
        download_type = request.POST.get('download_type', 'zip')
        
        if not photo_ids_str:
            return HttpResponse("No photos selected for download", status=400)
        
        photo_ids = [int(id) for id in photo_ids_str.split(',')]
        
        # Get the photos
        photos = EventPhoto.objects.filter(
            id__in=photo_ids,
            user_matches__user=request.user
        )
        
        # If no photos found or unauthorized
        if not photos:
            return HttpResponse("No photos found or unauthorized", status=404)
        
        # Handle single photo download
        if download_type == 'single' and len(photos) == 1:
            photo = photos.first()
            # Use enhanced image if available, otherwise use original
            image_file = photo.enhanced_image if photo.enhanced_image else photo.image
            file_name = os.path.basename(image_file.name)
            
            # Serve the file
            response = FileResponse(
                image_file.open('rb'),
                content_type='image/jpeg'  # Adjust if needed
            )
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        
        # Handle zip download for multiple photos
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for photo in photos:
                image_file = photo.enhanced_image if photo.enhanced_image else photo.image
                file_name = os.path.basename(image_file.name)
                
                # Add file to zip
                zipf.writestr(file_name, image_file.read())
        
        # Reset file pointer to beginning
        memory_file.seek(0)
        
        # Set proper response headers
        response = HttpResponse(memory_file, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="user_gallery.zip"'
        return response