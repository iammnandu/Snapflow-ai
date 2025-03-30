# quick_registration/models.py
from django.db import models
from django.urls import reverse
from events.models import Event
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import os
from django.conf import settings


class QuickRegistrationLink(models.Model):
    """Model to store quick registration links for events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='quick_registration_links')
    code = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    qr_code = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    
    def __str__(self):
        return f"Quick Registration for {self.event.title}"
    
    def get_absolute_url(self):
        return reverse('quick_registration:register', kwargs={'code': self.code})
    
    def get_full_url(self, request=None):
        """Generate the full URL for the registration link"""
        if request:
            base_url = f"{request.scheme}://{request.get_host()}"
        else:
            # Default to development environment
            base_url = "http://localhost:8000"
        
        return f"{base_url}{self.get_absolute_url()}"
    
    def generate_qr_code(self, request=None):
        """Generate QR code for the registration link"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(self.get_full_url(request))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        # Create a unique filename
        filename = f'event_{self.event.id}_qrcode_{self.code}.png'
        
        # Save the QR code
        self.qr_code.save(filename, File(buffer), save=False)
        self.save()
        
        return self.qr_code