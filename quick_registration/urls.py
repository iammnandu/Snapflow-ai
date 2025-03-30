# quick_registration/urls.py
from django.urls import path
from . import views

app_name = 'quick_registration'

urlpatterns = [
    # URLs for organizers
    path('event/<slug:event_slug>/create-link/', views.create_registration_link, name='create_link'),
    path('event/<slug:event_slug>/manage-links/', views.manage_registration_links, name='manage_links'),
    path('link/<int:link_id>/regenerate-qr/', views.regenerate_qr_code, name='regenerate_qr'),
    path('link/<int:link_id>/download-qr/', views.download_qr_code, name='download_qr'),
    
    # URL for participants
    path('register/<str:code>/', views.register_participant, name='register'),
]