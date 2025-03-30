"""
URL configuration for SnapFlow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('account/', include('users.urls')),
    path('events/', include('events.urls')),
    path('photos/', include('photos.urls')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('highlights/', include('highlights.urls', namespace='highlights')),
    path('privacy/', include('privacy.urls')),
    path('quick-registration/', include('quick_registration.urls', namespace='quick_registration')),


    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

