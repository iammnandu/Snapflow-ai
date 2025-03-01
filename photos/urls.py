# urls.py (updated)
from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    # Existing URLs
    path('<slug:slug>/gallery/', views.EventGalleryView.as_view(), name='event_gallery'),
    path('<slug:slug>/upload/', views.UploadPhotosView.as_view(), name='upload_photos'),
    path('photo/<int:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'),
    path('photo/<int:pk>/action/', views.PhotoActionView.as_view(), name='photo_action'),
    path('photo/<int:pk>/delete/', views.DeletePhotoView.as_view(), name='delete_photo'),
    path('photo/<int:pk>/comments/', views.photo_comments, name='photo_comments'),
    
    # New URLs for user gallery and related features
    path('my-gallery/', views.UserGalleryView.as_view(), name='user_gallery'),

    path('photo/<int:pk>/reanalyze-faces/', views.reanalyze_faces, name='reanalyze_faces'),
]