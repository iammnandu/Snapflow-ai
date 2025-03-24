# privacy/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone

from events.models import Event
from .models import PrivacyRequest, ProcessedPhoto
from .forms import PrivacyRequestForm, PrivacyRequestResponseForm


class ParticipantPrivacyRequestListView(LoginRequiredMixin, ListView):
    """View for participants to see their privacy requests."""
    model = PrivacyRequest
    template_name = 'privacy/participant_request_list.html'
    context_object_name = 'privacy_requests'
    
    def get_queryset(self):
        return PrivacyRequest.objects.filter(user=self.request.user)


class OrganizerPrivacyRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for organizers to manage privacy requests for their events."""
    model = PrivacyRequest
    template_name = 'privacy/organizer_request_list.html'
    context_object_name = 'privacy_requests'
    
    def test_func(self):
        """Check if user is an organizer."""
        return self.request.user.role == 'ORGANIZER'
    
    def get_queryset(self):
        """Get privacy requests for events organized by the user."""
        return PrivacyRequest.objects.filter(event__organizer=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get counts for different statuses
        context['pending_count'] = self.get_queryset().filter(status='pending').count()
        context['approved_count'] = self.get_queryset().filter(status='approved').count()
        context['processing_count'] = self.get_queryset().filter(status='processing').count()
        context['completed_count'] = self.get_queryset().filter(status='completed').count()
        context['rejected_count'] = self.get_queryset().filter(status='rejected').count()
        return context


class EventPrivacyRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for organizers to manage privacy requests for a specific event."""
    model = PrivacyRequest
    template_name = 'privacy/event_request_list.html'
    context_object_name = 'privacy_requests'
    
    def test_func(self):
        """Check if user is the organizer of this event."""
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        return event.organizer == self.request.user
    
    def get_queryset(self):
        """Get privacy requests for the specific event."""
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        return PrivacyRequest.objects.filter(event=event)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = get_object_or_404(Event, slug=self.kwargs['slug'])
        context['event'] = event
        return context


class PrivacyRequestCreateView(LoginRequiredMixin, CreateView):
    """View for participants to create a privacy request."""
    model = PrivacyRequest
    form_class = PrivacyRequestForm
    template_name = 'privacy/request_form.html'
    
    def get_success_url(self):
        return reverse('privacy:participant_requests')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['event'] = get_object_or_404(Event, slug=self.kwargs['slug'])
        return context
    
    def form_valid(self, form):
        """Set the user and event before saving."""
        form.instance.user = self.request.user
        form.instance.event = get_object_or_404(Event, slug=self.kwargs['slug'])
        
        # Check if a similar request already exists
        existing_request = PrivacyRequest.objects.filter(
            user=self.request.user,
            event=form.instance.event,
            request_type=form.instance.request_type
        ).first()
        
        if existing_request:
            messages.error(self.request, f"You already have a {form.instance.get_request_type_display()} request for this event with status: {existing_request.get_status_display()}")
            return redirect('privacy:participant_requests')
        
        messages.success(self.request, "Privacy request submitted successfully.")
        return super().form_valid(form)


class PrivacyRequestDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View for viewing details of a privacy request."""
    model = PrivacyRequest
    template_name = 'privacy/request_detail.html'
    context_object_name = 'privacy_request'
    
    def test_func(self):
        """Check if user is either the requester or the event organizer."""
        request = self.get_object()
        return (request.user == self.request.user or 
                request.event.organizer == self.request.user)


class PrivacyRequestResponseView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for organizers to respond to privacy requests."""
    model = PrivacyRequest
    form_class = PrivacyRequestResponseForm
    template_name = 'privacy/request_response_form.html'
    
    def test_func(self):
        """Check if user is the event organizer."""
        request = self.get_object()
        return request.event.organizer == self.request.user
    
    def get_success_url(self):
        """Redirect back to the event's privacy request list."""
        return reverse('privacy:event_requests', kwargs={'slug': self.object.event.slug})
    
    def form_valid(self, form):
        """Update the status and notify the participant."""
        privacy_request = self.get_object()
        
        # Check if status is changing from pending
        if privacy_request.status == 'pending':
            if form.cleaned_data['status'] == 'approved':
                messages.success(self.request, f"Privacy request approved. Photo processing will begin.")
                # Processing will be triggered by the signal
            elif form.cleaned_data['status'] == 'rejected':
                if not form.cleaned_data['rejection_reason']:
                    form.add_error('rejection_reason', 'Please provide a reason for rejection')
                    return self.form_invalid(form)
                messages.info(self.request, f"Privacy request has been rejected.")
            
        return super().form_valid(form)