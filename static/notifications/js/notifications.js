/**
 * Notifications handler for SnapFlow
 * Provides real-time notification functionality
 */

class NotificationHandler {
    constructor(options) {
        this.options = Object.assign({
            countSelector: '#notification-count',
            menuSelector: '#notification-menu',
            checkInterval: 30000,  // 30 seconds
            checkUrl: '/notifications/unread-count/',
            markReadUrl: '/notifications/{id}/mark-read/',
            listUrl: '/notifications/',
            fadeTime: 300,
        }, options);
        
        this.notificationCount = parseInt(document.querySelector(this.options.countSelector)?.textContent || '0');
        this.initialize();
    }
    
    initialize() {
        // Set up polling for new notifications
        this.startPolling();
        
        // Set up click handlers
        this.setupEventListeners();
    }
    
    startPolling() {
        this.intervalId = setInterval(() => {
            this.checkNotifications();
        }, this.options.checkInterval);
    }
    
    stopPolling() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
    
    setupEventListeners() {
        // Mark as read buttons
        document.querySelectorAll('.mark-read-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const notificationId = button.dataset.notificationId;
                this.markAsRead(notificationId);
            });
        });
        
        // Document visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.checkNotifications();
            }
        });
    }
    
    checkNotifications() {
        fetch(this.options.checkUrl, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.count !== this.notificationCount) {
                this.updateNotificationCount(data.count);
                
                // If there are new notifications, show a browser notification
                if (data.count > this.notificationCount) {
                    this.showBrowserNotification(data.count - this.notificationCount);
                }
            }
        })
        .catch(error => {
            console.error('Error checking notifications:', error);
        });
    }
    
    updateNotificationCount(count) {
        this.notificationCount = count;
        
        // Update the counter in the DOM
        const countElement = document.querySelector(this.options.countSelector);
        if (countElement) {
            countElement.textContent = count;
            
            // Show/hide the badge
            if (count > 0) {
                countElement.classList.remove('hidden');
            } else {
                countElement.classList.add('hidden');
            }
        }
    }
    
    markAsRead(notificationId) {
        const url = this.options.markReadUrl.replace('{id}', notificationId);
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update notification count
                this.updateNotificationCount(data.unread_count);
                
                // Visual feedback
                const notification = document.querySelector(`[data-notification-id="${notificationId}"]`);
                if (notification) {
                    notification.classList.remove('bg-blue-50');
                    notification.classList.add('bg-white');
                    
                    // Hide the read button
                    const readBtn = notification.querySelector('.mark-read-btn');
                    if (readBtn) {
                        readBtn.style.display = 'none';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }
    
    showBrowserNotification(newCount) {
        // Check if browser notifications are supported and permission granted
        if (!('Notification' in window)) {
            return;
        }
        
        if (Notification.permission === 'granted') {
            this.createBrowserNotification(newCount);
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    this.createBrowserNotification(newCount);
                }
            });
        }
    }
    
    createBrowserNotification(newCount) {
        const notificationText = newCount === 1 
            ? "You have 1 new notification" 
            : `You have ${newCount} new notifications`;
            
        const notification = new Notification('SnapFlow', {
            body: notificationText,
            icon: '/static/img/logo.png'
        });
        
        notification.onclick = () => {
            window.open(this.options.listUrl, '_blank');
        };
    }
    
    getCsrfToken() {
        // Get CSRF token from cookie
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith('csrftoken=')) {
                return cookie.substring('csrftoken='.length, cookie.length);
            }
        }
        return '';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.notificationHandler = new NotificationHandler();
});