import os

from celery import Celery
from celery.signals import task_postrun, worker_process_init

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('olx_notify')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@worker_process_init.connect
def _close_stale_db_connections(**kwargs):
    from django.db import close_old_connections

    close_old_connections()


@task_postrun.connect
def _close_db_connections_after_task(**kwargs):
    from django.db import close_old_connections

    close_old_connections()
