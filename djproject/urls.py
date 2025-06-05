from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('demo/', include('demo.urls')),
    path('tasklog/', include('celery_tasklog.urls')),
]
