"""
config/celery_app.py
Inisialisasi Celery. Sesuai Chapter 13 Section 4.3.
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('simple_lms')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(['api'])