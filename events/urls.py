# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # ----------------------------------------
    # Event Management
    # ----------------------------------------
    path('create/', views.EventCreateView.as_view(), name='event_create'),  
    path('list/', views.EventListView.as_view(), name='event_list'), 
    path('<slug:slug>/dashboard/', views.EventDashboardView.as_view(), name='event_dashboard'), 
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_edit'),
    path('<slug:slug>/setup/<str:step>/', views.EventSetupView.as_view(), name='event_setup'),
    path('<slug:slug>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    path('<slug:slug>/contact-organizer/', views.contact_organizer, name='contact_organizer'),

    # ----------------------------------------
    # Crew Management
    # ----------------------------------------
    path('<slug:slug>/crew/', views.CrewManagementView.as_view(), name='crew_management'),
    path('crew/invite/<str:token>/', views.accept_crew_invitation, name='accept_crew_invitation'),

    # ----------------------------------------
    # Participant Management
    # ----------------------------------------
    path('<slug:slug>/participants/', views.EventParticipantsView.as_view(), name='event_participants'),
    path('<slug:slug>/participants/add/', views.AddParticipantView.as_view(), name='add_participant'),
    path('<slug:slug>/participants/<int:participant_id>/edit/', views.EditParticipantView.as_view(), name='edit_participant'),
    path('<slug:slug>/participants/<int:participant_id>/remove/', views.RemoveParticipantView.as_view(), name='remove_participant'),
    path('<slug:slug>/participants/<int:participant_id>/resend-invite/', views.ResendParticipantInviteView.as_view(), name='resend_invite'),

    # ----------------------------------------
    # Equipment Configuration
    # ----------------------------------------
    path('<slug:slug>/equipment/', views.EquipmentConfigurationView.as_view(), name='equipment_config'),

    # ----------------------------------------
    # Access Requests
    # ----------------------------------------
    path('access/request/', views.request_access, name='request_access'),
    path('access/form/', views.RequestEventAccessView.as_view(), name='request_access_form'),
    path('requests/', views.access_requests_list, name='access_requests'),
    path('events/requests/<int:request_id>/approve/', views.approve_request, name='approve_request'),
    path('events/requests/<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('requests/cancel/<int:request_id>/', views.cancel_access_request, name='cancel_access_request'),

    # ----------------------------------------
    # Gallery Access Management
    # ----------------------------------------
    path('<slug:slug>/gallery-access/request/', views.RequestGalleryAccessView.as_view(), name='request_gallery_access'),
    path('<slug:slug>/gallery-access/manage/', views.ManageGalleryAccessView.as_view(), name='manage_gallery_access'),
    path('<slug:slug>/gallery-access/approve/<int:participant_id>/', views.approve_gallery_access, name='approve_gallery_access'),
    path('<slug:slug>/gallery-access/deny/<int:participant_id>/', views.deny_gallery_access, name='deny_gallery_access'),
]
