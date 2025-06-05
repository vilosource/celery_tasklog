from django.contrib import admin
from .models import TaskLogLine


@admin.register(TaskLogLine)
class TaskLogLineAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'timestamp', 'stream', 'message')
    list_filter = ('stream',)
    search_fields = ('task_id', 'message')
