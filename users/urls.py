# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    # Existing URLs
    path('register/', views.register, name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    # New dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('privacy/update/', views.update_privacy, name='update_privacy'),

    path("delete-account/", views.delete_account, name="delete_account"),

    path('testdashboard/', views.testdashboard, name='testdashboard'),
]