from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from celery import current_app
from django_celery_results.models import TaskResult
from django.conf import settings
from .models import TaskLogLine
from .serializers import TaskListSerializer, TaskDetailSerializer, TaskLogLineSerializer
import json
import time
import threading
import logging
import redis

# Import the global SSE connections dictionary and lock from signals.py
from .signals import sse_connections, sse_lock

logger = logging.getLogger(__name__)

# Redis client for streaming log updates
redis_client = redis.Redis.from_url(settings.CELERY_BROKER_URL)


class TaskListView(generics.ListAPIView):
    """API endpoint to list all tasks with their status"""
    serializer_class = TaskListSerializer
    
    def get_queryset(self):
        # Get tasks from django-celery-results
        return TaskResult.objects.all().order_by('-date_created')
    
    def list(self, request, *args, **kwargs):
        # Get tasks from Celery result backend
        tasks = []
        
        # Get from django-celery-results if available
        try:
            task_results = TaskResult.objects.all().order_by('-date_created')[:50]  # Limit to recent 50 tasks
            
            for task_result in task_results:
                # Get progress from meta if available
                progress = None
                if task_result.meta and isinstance(task_result.meta, dict):
                    progress = task_result.meta.get('progress')
                
                task_data = {
                    'task_id': task_result.task_id,
                    'task_name': task_result.task_name or 'Unknown',
                    'status': task_result.status,
                    'started_at': task_result.date_created,
                    'completed_at': task_result.date_done,
                    'progress': progress
                }
                tasks.append(task_data)
        except Exception as e:
            # Fallback: get from TaskLogLine if django-celery-results not available
            task_ids = TaskLogLine.objects.values_list('task_id', flat=True).distinct()[:50]
            for task_id in task_ids:
                # Try to get task info from Celery
                try:
                    result = current_app.AsyncResult(task_id)
                    progress = None
                    if result.info and isinstance(result.info, dict):
                        progress = result.info.get('progress')
                    
                    task_data = {
                        'task_id': task_id,
                        'task_name': result.name or 'Unknown',
                        'status': result.status,
                        'started_at': None,
                        'completed_at': None,
                        'progress': progress
                    }
                    tasks.append(task_data)
                except Exception:
                    # Basic task info from logs only
                    task_data = {
                        'task_id': task_id,
                        'task_name': 'Unknown',
                        'status': 'UNKNOWN',
                        'started_at': None,
                        'completed_at': None,
                        'progress': None
                    }
                    tasks.append(task_data)
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)


class TaskDetailView(generics.RetrieveAPIView):
    """API endpoint to get task details including logs"""
    serializer_class = TaskDetailSerializer
    lookup_field = 'task_id'
    
    def retrieve(self, request, task_id, *args, **kwargs):
        # Get task info from Celery
        try:
            result = current_app.AsyncResult(task_id)
            progress = None
            if result.info and isinstance(result.info, dict):
                progress = result.info.get('progress')
            
            # Try to get from django-celery-results for timestamps
            task_result = None
            try:
                task_result = TaskResult.objects.get(task_id=task_id)
            except TaskResult.DoesNotExist:
                pass
            
            task_data = {
                'task_id': task_id,
                'task_name': result.name or (task_result.task_name if task_result else 'Unknown'),
                'status': result.status,
                'started_at': task_result.date_created if task_result else None,
                'completed_at': task_result.date_done if task_result else None,
                'progress': progress,
                'result': result.result if result.successful() else None
            }
        except Exception:
            task_data = {
                'task_id': task_id,
                'task_name': 'Unknown',
                'status': 'UNKNOWN',
                'started_at': None,
                'completed_at': None,
                'progress': None,
                'result': None
            }
        
        # Get logs (last 1000 lines)
        logs = TaskLogLine.objects.filter(task_id=task_id).order_by('-id')[:1000]
        logs = list(reversed(logs))  # Reverse to get chronological order
        
        logger.info(f"Retrieved {len(logs)} log lines for task {task_id}")
        if logs:
            logger.info(f"Sample log: {logs[0]}")
        
        # Important: Always use the serializer to properly format the logs for JSON
        serializer = TaskLogLineSerializer(logs, many=True)
        task_data['logs'] = serializer.data
        task_data['log_count'] = len(logs)
        
        serializer = self.get_serializer(task_data)
        return Response(serializer.data)


@csrf_exempt
@api_view(['POST'])
def trigger_demo_task(request):
    """
    Optional API endpoint to trigger demo tasks.
    This function attempts to import and trigger demo tasks if available.
    If demo tasks are not available, it returns an error.
    """
    try:
        # Try to import demo tasks
        from demo.tasks import demo_long_task, demo_failing_task, demo_quick_task
    except ImportError:
        return Response({
            'error': 'Demo tasks not available. Make sure the demo app is installed and configured.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    task_type = request.data.get('task_type', 'long')
    duration = request.data.get('duration', 60)
    
    try:
        duration = int(duration)
        if duration < 1 or duration > 300:  # Limit between 1-300 seconds
            duration = 60
    except (ValueError, TypeError):
        duration = 60

    # Start the appropriate demo task
    if task_type == 'failing':
        result = demo_failing_task.delay()
        message = 'Demo failing task started'
    elif task_type == 'quick':
        result = demo_quick_task.delay()
        message = 'Demo quick task started'
    else:  # default to long task
        result = demo_long_task.delay(duration)
        message = f'Demo long task started with duration {duration} seconds'

    return Response({
        'task_id': result.id,
        'task_type': task_type,
        'duration': duration if task_type == 'long' else None,
        'message': message
    })


@csrf_exempt
def task_log_stream(request, task_id):
    """SSE endpoint for streaming task logs"""
    import queue
    
    logger.info(f"SSE connection requested for task {task_id}")
    logger.info(f"Current registered SSE connections: {list(sse_connections.keys())}")
    
    def event_stream():
        logger.info(f"Starting SSE stream for task {task_id}")
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n".encode('utf-8')

        # Register this connection
        connection_queue = queue.Queue()
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        channel_name = f"tasklog:{task_id}"
        pubsub.subscribe(channel_name)
        stop_event = threading.Event()

        def redis_listener():
            for message in pubsub.listen():
                if stop_event.is_set():
                    break
                if message.get('type') == 'message':
                    try:
                        data = json.loads(message['data'])
                        connection_queue.put_nowait(data)
                    except Exception as e:
                        logger.error(f"Error processing pubsub message: {e}")

        listener_thread = threading.Thread(target=redis_listener, daemon=True)
        listener_thread.start()
        with sse_lock:
            if task_id not in sse_connections:
                sse_connections[task_id] = []

            # Create a queue for this connection
            sse_connections[task_id].append(connection_queue)
            logger.info(f"Registered new SSE connection for task {task_id}, connections: {len(sse_connections[task_id])}")
        
        # Load existing logs and add them to the queue to ensure client has the latest
        existing_logs = TaskLogLine.objects.filter(task_id=task_id).order_by('id')
        logger.info(f"Found {existing_logs.count()} existing logs for task {task_id}")
        
        # Add existing logs to queue if there are any
        for log in existing_logs:
            message = {
                'type': 'new_log',
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'stream': log.stream,
                'message': log.message,
                'task_id': log.task_id
            }
            connection_queue.put_nowait(message)
        
        try:
            # Keep connection alive and send queued messages
            while True:
                try:
                    # Wait for new log messages (with timeout for keepalive)
                    message = connection_queue.get(timeout=5)  # 5 second timeout for faster keepalive
                    logger.debug(f"Sending message: {message['type']}")
                    yield f"data: {json.dumps(message)}\n\n".encode('utf-8')
                except queue.Empty:
                    # Send keepalive
                    logger.debug(f"Sending keepalive for task {task_id}")
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n".encode('utf-8')
                except Exception as e:
                    logger.error(f"SSE error for task {task_id}: {e}")
                    break
        finally:
            # Clean up connection
            logger.info(f"Cleaning up SSE connection for task {task_id}")
            stop_event.set()
            try:
                pubsub.close()
            except Exception:
                pass
            listener_thread.join(timeout=1)
            with sse_lock:
                if task_id in sse_connections:
                    try:
                        sse_connections[task_id].remove(connection_queue)
                        logger.info(f"Removed connection, remaining: {len(sse_connections[task_id])}")
                        if not sse_connections[task_id]:
                            del sse_connections[task_id]
                            logger.info(f"No more connections for task {task_id}, deleted entry")
                    except ValueError:
                        logger.error(f"Failed to remove connection from {task_id}")
                        pass
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    return response


# Signal handler is now in signals.py


@csrf_exempt
def test_sse(request):
    """Simple test SSE endpoint"""
    import time
    
    def simple_stream():
        yield b"data: {\"type\": \"test\", \"message\": \"connected\"}\n\n"
        for i in range(5):
            time.sleep(1)
            yield f"data: {{\"type\": \"test\", \"count\": {i}}}\n\n".encode('utf-8')
        yield b"data: {\"type\": \"test\", \"message\": \"done\"}\n\n"
    
    response = StreamingHttpResponse(simple_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Access-Control-Allow-Origin'] = '*'
    return response
