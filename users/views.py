from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    UserTypeSelectionForm, BasicRegistrationForm,
    OrganizerProfileForm, PhotographerProfileForm, ParticipantProfileForm
)


from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import BasicRegistrationForm

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


def select_user_type(request):
    if request.method == 'POST':
        form = UserTypeSelectionForm(request.POST)
        if form.is_valid():
            user_type = form.cleaned_data['role']
            request.session['selected_user_type'] = user_type
            return redirect('users:register')
    else:
        form = UserTypeSelectionForm()
    return render(request, 'users/select_user_type.html', {'form': form})


@login_required
def complete_profile(request):
    user = request.user
    
    # Select the appropriate form based on user role
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
def profile(request):
    user = request.user
    
    # Select the appropriate form based on user role
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
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        form = FormClass(instance=user)
    
    return render(request, 'users/profile.html', {
        'form': form,
        'user_type': user.get_role_display()
    })


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('users:login')