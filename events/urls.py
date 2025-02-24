from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Existing URLs
    path('create/', views.EventCreateView.as_view(), name='event_create'), #done
    path('<slug:slug>/setup/<str:step>/', views.EventSetupView.as_view(), name='event_setup'),
    path('<slug:slug>/dashboard/', views.EventDashboardView.as_view(), name='event_dashboard'), #done
    path('<slug:slug>/crew/', views.CrewManagementView.as_view(), name='crew_management'),
    path('<slug:slug>/equipment/', views.EquipmentConfigurationView.as_view(), name='equipment_config'),
    path('<slug:slug>/temp-profile/', views.create_temp_profile, name='create_temp_profile'),
    path('list/', views.EventListView.as_view(), name='event_list'), #done
    
    # Access request URLs
    path('access/request/', views.request_access, name='request_access'), #done
    path('access/request/<int:request_id>/', views.handle_access_request, name='handle_access_request'), #done

    # Missing URLs that match views in views.py
    path('access/form/', views.RequestEventAccessView.as_view(), name='request_access_form'), #done
    path('crew/invite/<str:token>/', views.accept_crew_invitation, name='accept_crew_invitation'), #done
    path('<slug:slug>/ai-features/', views.toggle_ai_features, name='toggle_ai_features'),
    path('<slug:slug>/', views.EventDashboardView.as_view(), name='event_detail'),
 
    path('events/requests/', views.access_requests_list, name='access_requests'), #done
    path('events/requests/<int:request_id>/approve/', views.approve_request, name='approve_request'), #done
    path('events/requests/<int:request_id>/reject/', views.reject_request, name='reject_request'), #done
 
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_edit'), #done


    path('<slug:slug>/gallery/', views.EventGalleryView.as_view(), name='event_gallery'), #done
    path('<slug:slug>/upload/', views.UploadPhotosView.as_view(), name='upload_photos'), #done
    path('photo/<int:pk>/', views.PhotoDetailView.as_view(), name='photo_detail'), #done
    path('photo/<int:pk>/action/', views.PhotoActionView.as_view(), name='photo_action'), #done
    path('photo/<int:pk>/delete/', views.DeletePhotoView.as_view(), name='delete_photo'), #done


]