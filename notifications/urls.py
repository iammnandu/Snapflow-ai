# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/', views.notification_detail, name='detail'),
    path('<int:notification_id>/mark-read/', views.mark_as_read, name='mark_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),  # Add this line
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_read'),
    path('preferences/', views.preferences, name='preferences'),
]
