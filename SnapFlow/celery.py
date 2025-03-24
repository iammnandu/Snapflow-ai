import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SnapFlow.settings')

app = Celery('SnapFlow')

# Use a string here because the worker doesn't have to serialize
# the configuration object to child processes
app.config_from_object('django.conf:settings', namespace='CELERY')


app.autodiscover_tasks(['users', 'events', 'photos', 'notifications', 'highlights', 'privacy'])
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')