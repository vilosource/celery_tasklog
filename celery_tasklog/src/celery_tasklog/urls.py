from django.urls import path, include
from . import views, api_views

app_name = 'celery_tasklog'

# API URLs for task management (reusable by any app)
api_urlpatterns = [
    path('tasks/', api_views.TaskListView.as_view(), name='task_list'),
    path('tasks/<str:task_id>/', api_views.TaskDetailView.as_view(), name='task_detail'),
]

# SSE URLs for real-time log streaming (reusable by any app)
sse_urlpatterns = [
    path('task/<str:task_id>/', api_views.task_log_stream, name='task_log_stream'),
    path('test/', api_views.test_sse, name='test_sse'),
]

urlpatterns = [
    # Basic task log views
    path('task/<str:task_id>/', views.task_log_view, name='task_log'),
    path('diagnostic/', views.task_diagnostic, name='task_diagnostic'),
    
    # API endpoints (reusable)
    path('api/', include(api_urlpatterns)),
    
    # SSE endpoints (reusable)  
    path('sse/', include(sse_urlpatterns)),
]
