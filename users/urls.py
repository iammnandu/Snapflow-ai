# users/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html',redirect_authenticated_user=True), name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("delete-account/", views.delete_account, name="delete_account"),
    path('connections/', views.connections, name='connections'),
]