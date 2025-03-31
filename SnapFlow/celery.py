import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SnapFlow.settings')

app = Celery('SnapFlow')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['users', 'events', 'photos', 'notifications', 'highlights', 'privacy'])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Celery Beat Schedule
app.conf.beat_schedule = {
    'process-morning-email-batch': {
        'task': 'notifications.tasks.process_morning_email_batch',
        'schedule': crontab(hour=9, minute=0),  # Run at 9:00 AM
    },
    'process-evening-email-batch': {
        'task': 'notifications.tasks.process_evening_email_batch',
        'schedule': crontab(hour=17, minute=0),  # Run at 5:00 PM
    },
    'send-daily-digest': {
        'task': 'notifications.tasks.send_daily_digest',
        'schedule': crontab(hour=18, minute=0),  # Run at 6:00 PM
    },
    'send-weekly-digest': {
        'task': 'notifications.tasks.send_weekly_digest',
        'schedule': crontab(day_of_week=0, hour=10, minute=0),  # Run at 10:00 AM on Sundays
    },
}
