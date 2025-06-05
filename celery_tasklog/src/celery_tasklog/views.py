from django.shortcuts import render
from .models import TaskLogLine


def task_log_view(request, task_id):
    logs = TaskLogLine.objects.filter(task_id=task_id).order_by('timestamp')
    return render(request, 'celery_tasklog/task_view.html', {'logs': logs, 'task_id': task_id})


def task_diagnostic(request):
    return render(request, 'celery_tasklog/diagnostic.html')
