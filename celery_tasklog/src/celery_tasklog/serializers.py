from rest_framework import serializers
from celery import current_app
from django_celery_results.models import TaskResult
from .models import TaskLogLine


class TaskLogLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskLogLine
        fields = ['id', 'timestamp', 'stream', 'message']


class TaskListSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    task_name = serializers.CharField()
    status = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    progress = serializers.IntegerField(allow_null=True)


class TaskDetailSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    task_name = serializers.CharField() 
    status = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    progress = serializers.IntegerField(allow_null=True)
    result = serializers.JSONField(allow_null=True)
    logs = TaskLogLineSerializer(many=True)
    log_count = serializers.IntegerField()
