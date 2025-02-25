from django.urls import path
from . import views

app_name = "photos"

urlpatterns = [

    path('<slug:slug>/gallery/', views.EventGalleryView.as_view(), name='event_gallery'), #done
    path('<slug:slug>/upload/', views.UploadPhotosView.as_view(), name='upload_photos'), #done
    path('photo/<int:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'), #done
    path('photo/<int:pk>/action/', views.PhotoActionView.as_view(), name='photo_action'), #done
    path('photo/<int:pk>/delete/', views.DeletePhotoView.as_view(), name='delete_photo'), #done
    path('photo/<int:pk>/comments/', views.photo_comments, name='photo_comments'), #done

]