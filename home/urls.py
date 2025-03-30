from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('maintanance/',views.get_maintanence_page, name='maintanance'),
]