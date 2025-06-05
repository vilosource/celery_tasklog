from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import TaskLogLine
import json
import logging
import redis

logger = logging.getLogger(__name__)

# Redis client for broadcasting log lines
redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)

# NOTE:
# Celery workers run in separate processes from the Django application that
# serves the SSE streams.  Using in-memory data structures to keep track of
# connections here would therefore never work.  Connection management now
# lives entirely in the Django view and this signal simply publishes new log
# lines to Redis so any listening consumers can pick them up.



@receiver(post_save, sender=TaskLogLine)
def broadcast_new_log(sender, instance, created, **kwargs):
    """Broadcast new log lines to SSE connections"""
    logger.debug(f"Signal received for log line: {instance.id} for task {instance.task_id}")
    if created:
        message = {
            'type': 'new_log',
            'id': instance.id,
            'timestamp': instance.timestamp.isoformat(),
            'stream': instance.stream,
            'message': instance.message,
            'task_id': instance.task_id
        }

        # Publish to Redis channel for real-time updates
        try:
            redis_client.publish(f"tasklog:{instance.task_id}", json.dumps(message))
        except Exception as e:
            logger.error(f"Redis publish failed for task {instance.task_id}: {e}")

        # Connection management happens in the Django web process. Workers only
        # publish to Redis so any subscribed web consumers can relay the data.
