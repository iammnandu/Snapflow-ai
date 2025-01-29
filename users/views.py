from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, UserProfileForm, UserPreferencesForm
from .models import CustomUser, UserPreferences

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Use get_or_create to avoid IntegrityError
            user_preferences, created = UserPreferences.objects.get_or_create(user=user)
            
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('users:profile')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        preferences_form = UserPreferencesForm(request.POST, instance=request.user.userpreferences)
        if user_form.is_valid() and preferences_form.is_valid():
            user_form.save()
            preferences_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        preferences_form = UserPreferencesForm(instance=request.user.userpreferences)
    
    return render(request, 'users/profile.html', {
        'user_form': user_form,
        'preferences_form': preferences_form
    })
