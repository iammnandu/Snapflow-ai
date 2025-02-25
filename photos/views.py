from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, View
from django.http import JsonResponse
from django.core.paginator import Paginator
from photos.models import EventPhoto, PhotoLike, PhotoComment
from events.models import Event
from django.db.models import F
from django.contrib import messages  # Ensure this import is correct

class EventGalleryView(DetailView):
    model = Event
    template_name = 'photos/gallery.html'
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
            return redirect('photos:event_gallery', slug=slug)
        
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
            return redirect('photos:event_gallery', slug=event.slug)
        
        photo.delete()
        messages.success(request, "Photo deleted successfully.")
        return redirect('photos:event_gallery', slug=event.slug)
    

