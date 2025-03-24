# privacy/urls.py
from django.urls import path
from . import views

app_name = 'privacy'

urlpatterns = [
    # Participant URLs
    path('requests/', views.ParticipantPrivacyRequestListView.as_view(), name='participant_requests'),
    path('requests/<int:pk>/', views.PrivacyRequestDetailView.as_view(), name='request_detail'),
    path('event/<slug:slug>/request/', views.PrivacyRequestCreateView.as_view(), name='create_request'),
    
    # Organizer URLs
    path('manage/', views.OrganizerPrivacyRequestListView.as_view(), name='organizer_requests'),
    path('event/<slug:slug>/requests/', views.EventPrivacyRequestListView.as_view(), name='event_requests'),
    path('requests/<int:pk>/respond/', views.PrivacyRequestResponseView.as_view(), name='respond_to_request'),
]