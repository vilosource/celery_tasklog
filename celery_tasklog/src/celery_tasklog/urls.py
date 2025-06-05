from django.urls import path
from . import views

urlpatterns = [
    path('task/<str:task_id>/', views.task_log_view, name='task_log'),
    path('diagnostic/', views.task_diagnostic, name='task_diagnostic'),
]
