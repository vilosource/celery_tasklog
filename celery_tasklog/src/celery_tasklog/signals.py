from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import TaskLogLine
import json
import threading
import logging
import redis

logger = logging.getLogger(__name__)

# Redis client for broadcasting log lines
redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)

# Global dictionary to store SSE connections per task
# This needs to be imported in api_views.py
sse_connections = {}
sse_lock = threading.Lock()



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

        # Send to all connections for this task
        with sse_lock:
            logger.debug(f"Checking connections for task: {instance.task_id}. Active connections: {list(sse_connections.keys())}")
            if instance.task_id in sse_connections:
                # Send to all connections for this task
                logger.debug(f"Found {len(sse_connections[instance.task_id])} connections for task {instance.task_id}")
                dead_connections = []
                for connection_queue in sse_connections[instance.task_id]:
                    try:
                        connection_queue.put_nowait(message)
                        logger.debug(f"Message put in queue for task {instance.task_id}")
                    except Exception as e:
                        logger.error(f"Error adding message to queue: {e}")
                        dead_connections.append(connection_queue)
                
                # Clean up dead connections
                for dead_conn in dead_connections:
                    try:
                        sse_connections[instance.task_id].remove(dead_conn)
                    except ValueError:
                        pass
                
                # Remove task entry if no more connections
                if not sse_connections[instance.task_id]:
                    del sse_connections[instance.task_id]
            else:
                logger.debug(f"No active SSE connections for task {instance.task_id}")
