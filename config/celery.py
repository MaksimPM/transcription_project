import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    task_soft_time_limit=3600,
    task_time_limit=3600,
    broker_transport_options={'visibility_timeout': 43200},
    result_expires=3600,
)


# Load task modules from all registered Django apps.
app.autodiscover_tasks()
