from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add any additional context needed for the profile template
        context.update({
            'user': user,
            'profile_complete': bool(user.phone_number),  # Basic check for profile completion
        })
        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')
    
    def get_form_class(self):
        form_classes = {
            'ORGANIZER': OrganizerProfileForm,
            'PHOTOGRAPHER': PhotographerProfileForm,
            'PARTICIPANT': ParticipantProfileForm
        }
        return form_classes.get(self.request.user.role)
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!'
            })
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
        return super().form_invalid(form)

# Keep your existing views
def auth_view(request):
    """Combined login and registration view"""
    return render(request, 'users/auth.html')

def register(request):
    if request.method == 'POST':
        form = BasicRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = request.POST.get('role')
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful! Please complete your profile.')
            return redirect('users:complete_profile')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
            return redirect('users:auth')
    return redirect('users:auth')

@login_required
def complete_profile(request):
    user = request.user
    
    form_classes = {
        'ORGANIZER': OrganizerProfileForm,
        'PHOTOGRAPHER': PhotographerProfileForm,
        'PARTICIPANT': ParticipantProfileForm
    }
    
    FormClass = form_classes.get(user.role)
    
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile completed successfully!')
            return redirect('users:profile')
    else:
        form = FormClass(instance=user)
    
    return render(request, 'users/complete_profile.html', {
        'form': form,
        'user_type': user.get_role_display()
    })

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('users:login')