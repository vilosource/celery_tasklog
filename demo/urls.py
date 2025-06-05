from django.urls import path
from . import views

app_name = 'demo'

urlpatterns = [
    # Demo pages
    path('', views.demo_home, name='demo_home'),
    path('task/<str:task_id>/', views.demo_task_detail, name='demo_task_detail'),
]
