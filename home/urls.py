from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('home/', views.index, name='index'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]