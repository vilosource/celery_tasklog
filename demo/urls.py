from django.urls import path
from . import views

urlpatterns = [
    path('', views.demo_view, name='demo'),
]
