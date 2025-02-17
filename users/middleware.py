# users/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.urls.exceptions import NoReverseMatch

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return None

        # List of URLs that should be accessible even with incomplete profile
        exempt_urls = [
            reverse('users:complete_profile'),
            reverse('users:logout'),
            '/admin/',  # Admin URLs should be accessible
        ]

        # Check if current URL is exempt
        if any(request.path.startswith(url) for url in exempt_urls):
            return None

        # Skip middleware for admin users
        if request.user.is_staff or request.user.is_superuser:
            return None

        # Check if profile is complete based on user role
        if not self.is_profile_complete(request.user):
            messages.warning(
                request, 
                'Please complete your profile to access all features.'
            )
            return redirect('users:complete_profile')

        return None

    def is_profile_complete(self, user):
        """
        Check if user profile is complete based on role-specific requirements
        """
        # Common required fields for all users
        if not user.avatar or not user.phone_number:
            return False

        # Role-specific checks
        if user.role == 'ORGANIZER':
            if not user.company_name or not user.website:
                return False

        elif user.role == 'PHOTOGRAPHER':
            if not user.portfolio_url or not user.photographer_role:
                return False
            # Watermark is optional, so not checking for it

        elif user.role == 'PARTICIPANT':
            if not user.participant_type or not user.image_visibility:
                return False
            # blur_requested and remove_requested are boolean fields 
            # that default to False, so no need to check them

        return True