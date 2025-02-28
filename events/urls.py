from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Event Management
    path('create/', views.EventCreateView.as_view(), name='event_create'),  # done
    path('list/', views.EventListView.as_view(), name='event_list'),  # done
    path('<slug:slug>/', views.EventDashboardView.as_view(), name='event_detail'),
    path('<slug:slug>/dashboard/', views.EventDashboardView.as_view(), name='event_dashboard'),  # done
    path('<slug:slug>/edit/', views.EventUpdateView.as_view(), name='event_edit'),  # done
    path('<slug:slug>/setup/<str:step>/', views.EventSetupView.as_view(), name='event_setup'),
    path('<slug:slug>/ai-features/', views.toggle_ai_features, name='toggle_ai_features'),

    # Crew Management
    path('<slug:slug>/crew/', views.CrewManagementView.as_view(), name='crew_management'),
    path('crew/invite/<str:token>/', views.accept_crew_invitation, name='accept_crew_invitation'),  # done

    # Participant Management
    path('<slug:slug>/participants/', views.EventParticipantsView.as_view(), name='event_participants'),
    path('<slug:slug>/participants/add/', views.AddParticipantView.as_view(), name='add_participant'),
    path('<slug:slug>/participants/<int:participant_id>/edit/', views.EditParticipantView.as_view(), name='edit_participant'),
    path('<slug:slug>/participants/<int:participant_id>/remove/', views.RemoveParticipantView.as_view(), name='remove_participant'),
    path('<slug:slug>/participants/<int:participant_id>/resend-invite/', views.ResendParticipantInviteView.as_view(), name='resend_invite'),

    # Equipment Configuration
    path('<slug:slug>/equipment/', views.EquipmentConfigurationView.as_view(), name='equipment_config'),  # done

    # Temporary Profiles
    path('<slug:slug>/temp-profile/', views.create_temp_profile, name='create_temp_profile'),

    # Access Requests
    path('access/request/', views.request_access, name='request_access'),  # done

    path('access/form/', views.RequestEventAccessView.as_view(), name='request_access_form'),  # done
    path('events/requests/', views.access_requests_list, name='access_requests'),  # done
    path('events/requests/<int:request_id>/approve/', views.approve_request, name='approve_request'),  # done
    path('events/requests/<int:request_id>/reject/', views.reject_request, name='reject_request'),  # done

    path('requests/cancel/<int:request_id>/', views.cancel_access_request, name='cancel_access_request'),
]
