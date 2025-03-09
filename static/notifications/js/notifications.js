// Function to update notification badge count
function updateNotificationCount() {
    fetch('/notifications/unread-count/')
        .then(response => response.json())
        .then(data => {
            const count = data.count;
            const badge = document.querySelector('#notification-badge');
            
            if (badge) {
                // Update the badge indicator
                let indicator = badge.querySelector('span.absolute');
                
                if (count > 0) {
                    if (!indicator) {
                        // Create the indicator if it doesn't exist
                        indicator = document.createElement('span');
                        indicator.classList.add('absolute', 'top-0', 'right-0', 'block', 'h-2', 'w-2', 'rounded-full', 'bg-red-500', 'ring-2', 'ring-white');
                        badge.querySelector('a').appendChild(indicator);
                    }
                } else if (indicator) {
                    // Remove the indicator if count is 0
                    indicator.remove();
                }
            }
        })
        .catch(error => console.error('Error fetching notification count:', error));
}

// Mark notification as read
function markAsRead(notificationId, element) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/notifications/${notificationId}/mark-read/`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI
            const listItem = element.closest('li');
            listItem.classList.remove('bg-blue-50');
            updateNotificationCount();
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

// Delete notification
function deleteNotification(notificationId, element) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(`/notifications/${notificationId}/delete/`, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the notification from the list
            const listItem = element.closest('li');
            listItem.remove();
            updateNotificationCount();
        }
    })
    .catch(error => console.error('Error deleting notification:', error));
}

// Initialize WebSocket for real-time notifications (if WebSockets are configured)
function initializeNotificationSocket() {
    // Check if WebSocket is supported and a URL is provided by the server
    const socketUrl = document.querySelector('meta[name="notification-socket-url"]')?.content;
    if (!socketUrl) return;
    
    const socket = new WebSocket(socketUrl);
    
    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'notification') {
            // Update notification count
            updateNotificationCount();
            
            // Show a browser notification if permissions granted
            if (Notification.permission === 'granted' && data.notification) {
                const notification = new Notification(data.notification.title, {
                    body: data.notification.message,
                    icon: '/static/images/logo.png'
                });
                
                notification.onclick = function() {
                    window.open(data.notification.action_url, '_blank');
                };
            }
        }
    };
    
    socket.onclose = function() {
        console.log('Notification socket closed. Reconnecting in 5 seconds...');
        setTimeout(initializeNotificationSocket, 5000);
    };
}

// Request browser notification permission
function requestNotificationPermission() {
    if ('Notification' in window) {
        if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
            Notification.requestPermission();
        }
    }
}

// Document ready function
document.addEventListener('DOMContentLoaded', function() {
    // Initial notification count update
    updateNotificationCount();
    
    // Set up polling for notification updates (every 30 seconds)
    setInterval(updateNotificationCount, 30000);
    
    // Request notification permission
    requestNotificationPermission();
    
    // Initialize WebSocket for real-time updates
    initializeNotificationSocket();
    
    // Add event listeners for read/delete buttons
    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const notificationId = this.dataset.id;
            markAsRead(notificationId, this);
        });
    });
    
    document.querySelectorAll('.delete-notification-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const notificationId = this.dataset.id;
            deleteNotification(notificationId, this);
        });
    });
});