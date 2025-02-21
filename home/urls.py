from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='landing'),
    path('home/', views.index, name='index'),
    path('features/', views.get_features, name='features'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('maintanance/',views.get_maintanence_page, name='maintanance'),
]