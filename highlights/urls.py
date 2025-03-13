from django.urls import path
from . import views

app_name = 'highlights'

urlpatterns = [
    path('events/<slug:event_slug>/highlights/', views.event_highlights, name='event_highlights'),
    path('events/<slug:event_slug>/duplicates/', views.duplicate_photos, name='duplicate_photos'),
    path('duplicates/group/<int:group_id>/', views.duplicate_group_detail, name='duplicate_group_detail'),
    path('duplicates/select-primary/<int:group_id>/<int:photo_id>/', views.select_primary_photo, name='select_primary_photo'),


    path('duplicates/group/<int:group_id>/delete-photos/', views.delete_duplicate_photos, name='delete_duplicate_photos'),
]