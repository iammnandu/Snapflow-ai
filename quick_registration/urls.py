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
    path('link/<int:link_id>/delete/', views.delete_link, name='delete_link'),
    
    # New event card URLs
    path('link/<int:link_id>/generate-card/', views.generate_event_card, name='generate_card'),
    path('link/<int:link_id>/generate-card/<str:format_type>/', views.generate_event_card, name='generate_card_format'),
    path('link/<int:link_id>/download-card/image/', views.download_event_card, {'format_type': 'image'}, name='download_card_image'),
    path('link/<int:link_id>/download-card/pdf/', views.download_event_card, {'format_type': 'pdf'}, name='download_card_pdf'),
    
    # URL for participants
    path('register/<str:code>/', views.register_participant, name='register'),
]