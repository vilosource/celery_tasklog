from django.apps import AppConfig


class CeleryTaskLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "celery_tasklog"
    
    def ready(self):
        # Import signal handlers to ensure they are registered
        import celery_tasklog.signals
