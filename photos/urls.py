# photos/urls.py
from django.urls import path
from . import views

app_name = 'photos'

urlpatterns = [
    # Event Gallery Management
    path('<slug:slug>/gallery/', views.EventGalleryView.as_view(), name='event_gallery'),
    path('<slug:slug>/upload/', views.UploadPhotosView.as_view(), name='upload_photos'),
    
    # Individual Photo Management
    path('photo/<int:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'),
    path('photo/<int:pk>/action/', views.PhotoActionView.as_view(), name='photo_action'),
    path('photo/<int:pk>/delete/', views.DeletePhotoView.as_view(), name='delete_photo'),
    path('photo/<int:pk>/comments/', views.photo_comments, name='photo_comments'),
    path('photo/<int:pk>/reanalyze-faces/', views.reanalyze_faces, name='reanalyze_faces'),

    # User Gallery
    path('my-gallery/', views.UserGalleryView.as_view(), name='user_gallery'),

    # Photo Download
    path('event/<slug:slug>/download/', views.download_photos, name='download_photos'),
    path('download/', views.DownloadPhotosView.as_view(), name='download_photos'),
]
