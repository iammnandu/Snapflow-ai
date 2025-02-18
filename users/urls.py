from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.auth_view, name='auth'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='users/auth.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.ProfileUpdateView.as_view(), name='profile_update'),
]