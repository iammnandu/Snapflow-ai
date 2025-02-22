from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Existing URLs
    path('create/', views.EventCreateView.as_view(), name='event_create'),
    path('<slug:slug>/setup/<str:step>/', views.EventSetupView.as_view(), name='event_setup'),
    path('<slug:slug>/dashboard/', views.EventDashboardView.as_view(), name='event_dashboard'),
    path('<slug:slug>/crew/', views.CrewManagementView.as_view(), name='crew_management'),
    path('<slug:slug>/equipment/', views.EquipmentConfigurationView.as_view(), name='equipment_config'),
    path('<slug:slug>/gallery/', views.EventGalleryView.as_view(), name='event_gallery'),
    path('<slug:slug>/temp-profile/', views.create_temp_profile, name='create_temp_profile'),
    path('list/', views.EventListView.as_view(), name='event_list'),
    
    # Access request URLs
    path('access/request/', views.request_access, name='request_access'),
    path('access/request/<int:request_id>/', views.handle_access_request, name='handle_access_request'),

    # Missing URLs that match views in views.py
    path('access/form/', views.RequestEventAccessView.as_view(), name='request_access_form'),
    path('crew/invite/<str:token>/', views.accept_crew_invitation, name='accept_crew_invitation'),
    path('<slug:slug>/ai-features/', views.toggle_ai_features, name='toggle_ai_features'),
    path('<slug:slug>/', views.EventDashboardView.as_view(), name='event_detail'),

    path('events/requests/', views.access_requests_list, name='access_requests'),
    path('events/requests/<int:request_id>/approve/', views.approve_request, name='approve_request'),
    path('events/requests/<int:request_id>/reject/', views.reject_request, name='reject_request'),

    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_edit'),
]