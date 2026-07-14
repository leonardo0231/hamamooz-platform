import os

from celery import Celery

<<<<<<< HEAD
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
=======
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production"
)
>>>>>>> d1ab717a752428a109c9478b838e8338dccd9265

app = Celery("hamamooz")

app.config_from_object(
    "django.conf:settings", 
    namespace="CELERY"
)

app.autodiscover_tasks()
