import os
from celery import Celery

# Set default Django settings module for celery program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dmresponder.settings')

app = Celery('dmresponder')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
app.autodiscover_tasks(['instagram'], related_name='action_tasks')
