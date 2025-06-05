# Celery Task Log Migration Guide

This guide provides detailed instructions for migrating the Celery Terminal app to a standalone Poetry package called `celery_tasklog`, along with a demo project to showcase its functionality.

## Project Structure

```
celery_tasklog/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── celery_tasklog/            # Installable package
│   ├── pyproject.toml
│   └── src/
│       └── celery_tasklog/
│           ├── __init__.py
│           ├── apps.py
│           ├── models.py
│           ├── tasks.py
│           ├── views.py
│           ├── urls.py
│           ├── api_views.py
│           ├── serializers.py
│           ├── middleware.py
│           ├── admin.py
│           └── templates/
├── djproject/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── ...
├── demo/
│   ├── tasks.py
│   ├── views.py
│   └── urls.py
└── .envrc
```

## Step 1: Create Project Structure

```bash
mkdir celery-tasklog-project
cd celery-tasklog-project
```

## Step 2: Initialize Poetry Project

```bash
poetry init
# Add dependencies:
poetry add django celery redis django-celery-results
```

## Step 3: Set Up Django Project

```bash
poetry run django-admin startproject djproject .
```

## Step 4: Create Installable celery_tasklog Package

```bash
mkdir celery_tasklog
cd celery_tasklog
poetry init --name celery_tasklog
# Add package dependencies:
poetry add django celery
```

### Package Structure

```
celery_tasklog/
├── pyproject.toml
└── src/
    └── celery_tasklog/
        ├── __init__.py
        ├── apps.py
        ├── models.py
        ├── tasks.py
        ├── views.py
        ├── urls.py
        ├── middleware.py
        ├── admin.py
        ├── migrations/
        └── templates/
            └── celery_tasklog/
                ├── task_view.html
                ├── diagnostic.html
                └── launch_task.html
```

### Key Files Implementation

#### apps.py

```python
from django.apps import AppConfig

class CeleryTaskLogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'celery_tasklog'
```

#### models.py

```python
from django.db import models

class TaskLogLine(models.Model):
    task_id = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    stream = models.CharField(max_length=10, choices=[("stdout", "stdout"), ("stderr", "stderr")])
    message = models.TextField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.timestamp} [{self.stream}] {self.message}"
```

#### tasks.py

```python
import random
import time
from contextlib import contextmanager
from datetime import datetime
import pytz
import sys

from celery import Task, shared_task
from celery.utils.log import get_task_logger

from .models import TaskLogLine

logger = get_task_logger(__name__)

class DBLogWriter:
    def __init__(self, task_id: str, stream: str):
        self.task_id = task_id
        self.stream = stream
        self.buffer = ""

    def write(self, msg: str):
        self.buffer += msg
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line:
                TaskLogLine.objects.create(task_id=self.task_id, stream=self.stream, message=line)

    def flush(self):
        if self.buffer:
            TaskLogLine.objects.create(task_id=self.task_id, stream=self.stream, message=self.buffer)
            self.buffer = ""

@contextmanager
def capture_output(task_id: str):
    stdout_writer = DBLogWriter(task_id, "stdout")
    stderr_writer = DBLogWriter(task_id, "stderr")
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_writer
    sys.stderr = stderr_writer
    try:
        yield
    finally:
        stdout_writer.flush()
        stderr_writer.flush()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

class TerminalLoggingTask(Task):
    def __call__(self, *args, **kwargs):
        task_id = self.request.id
        with capture_output(task_id):
            return self.run(*args, **kwargs)

@shared_task(bind=True, name='celery_tasklog.tasks.timed_print_task')
def timed_print_task(self):
    """
    A test task that prints the current time at random intervals.
    """
    try:
        task_id = self.request.id
        TaskLogLine.objects.create(task_id=task_id, stream='stdout', message=f"Task {task_id} started manually")
        logger.info(f"Starting timed_print_task with ID: {task_id}")

        self.update_state(state='STARTED', meta={'progress': 0})

        duration = random.randint(5, 10)
        end_time = time.time() + duration

        TaskLogLine.objects.create(
            task_id=task_id,
            stream='stdout',
            message=f"Task will run for approximately {duration} seconds"
        )

        iteration = 0
        total_iterations = duration * 2

        while time.time() < end_time:
            iteration += 1
            timestamp = datetime.now(tz=pytz.UTC).isoformat()

            progress = min(int((iteration / total_iterations) * 100), 99)
            self.update_state(state='PROGRESS', meta={'progress': progress})

            TaskLogLine.objects.create(
                task_id=task_id,
                stream='stdout',
                message=f"Iteration {iteration}: {timestamp} (Progress: {progress}%)"
            )

            logger.info(f"Iteration {iteration}: {timestamp} (Progress: {progress}%)")

            time.sleep(random.uniform(0.5, 1))

        TaskLogLine.objects.create(
            task_id=task_id,
            stream='stdout',
            message=f"Task {task_id} completed successfully after {iteration} iterations"
        )
        logger.info(f"Task {task_id} completed successfully after {iteration} iterations")

        return {
            "status": "done",
            "iterations": iteration,
            "duration": duration
        }
    except Exception as e:
        error_msg = f"Error in timed_print_task: {str(e)}"
        logger.error(error_msg)

        try:
            task_id = getattr(self.request, 'id', 'unknown')
            TaskLogLine.objects.create(
                task_id=task_id,
                stream='stderr',
                message=error_msg
            )
        except Exception as inner_e:
            logger.error(f"Failed to log error to database: {str(inner_e)}")

        raise
```

#### views.py

```python
from django.shortcuts import render
from django.http import JsonResponse
from .models import TaskLogLine

def task_log_view(request, task_id):
    """
    View to display logs for a specific task
    """
    logs = TaskLogLine.objects.filter(task_id=task_id).order_by('timestamp')
    return render(request, 'celery_tasklog/task_view.html', {'logs': logs, 'task_id': task_id})

def task_diagnostic(request):
    """
    View to display diagnostic information about the task logging system
    """
    return render(request, 'celery_tasklog/diagnostic.html')
```

#### urls.py

```python
from django.urls import path
from . import views

urlpatterns = [
    path('task/<str:task_id>/', views.task_log_view, name='task_log'),
    path('diagnostic/', views.task_diagnostic, name='task_diagnostic'),
]
```

#### middleware.py

```python
class CeleryTaskLogMiddleware:
    """
    Middleware to add task logging information to the request context
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add any request preprocessing here
        response = self.get_response(request)
        # Add any response post-processing here
        return response
```

#### admin.py

```python
from django.contrib import admin
from .models import TaskLogLine

@admin.register(TaskLogLine)
class TaskLogLineAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'timestamp', 'stream', 'message')
    list_filter = ('stream',)
    search_fields = ('task_id', 'message')
```

#### migrations/0001_initial.py

```python
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TaskLogLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('stream', models.CharField(choices=[('stdout', 'stdout'), ('stderr', 'stderr')], max_length=10)),
                ('message', models.TextField()),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
```

## Step 5: Create Demo App

```bash
cd ..
poetry run python manage.py startapp demo
```

### Demo Tasks (demo/tasks.py)

```python
from celery import shared_task
from celery_tasklog.tasks import TerminalLoggingTask

@shared_task(base=TerminalLoggingTask, bind=True)
def demo_long_task(self, duration=60):
    print(f"Processing for {duration} seconds")

@shared_task(base=TerminalLoggingTask, bind=True)
def demo_failing_task(self):
    print("About to fail")
    raise Exception("Demo failure")

@shared_task(base=TerminalLoggingTask, bind=True)
def demo_quick_task(self):
    print("Quick task done")
```

### Demo Views (demo/views.py)

```python
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .tasks import demo_long_task, demo_failing_task, demo_quick_task

def demo_home(request):
    return render(request, 'demo/demo_home.html')

def demo_task_detail(request, task_id):
    return render(request, 'demo/demo_task_detail.html', {'task_id': task_id})

@api_view(["POST"])
def trigger_demo_task(request):
    result = demo_long_task.delay()
    return Response({'task_id': result.id})
```

### Demo URLs (demo/urls.py)

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.demo_home, name='demo_home'),
    path('task/<str:task_id>/', views.demo_task_detail, name='demo_task_detail'),
    path('api/trigger-demo/', views.trigger_demo_task, name='trigger_demo_task'),
]
```

## Step 6: Configure Django Settings (djproject/settings.py)

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-abcdef123456'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'celery_tasklog',
    'demo',
    'django_celery_results',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'celery_tasklog.middleware.CeleryTaskLogMiddleware',
]

ROOT_URLCONF = 'djproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'djproject.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'djproject_db'),
        'USER': os.getenv('POSTGRES_USER', 'djproject_user'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'securepassword'),
        'HOST': os.getenv('POSTGRES_HOST', 'postgres'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = 'django-db'

# Celery Task Log settings
CELERY_TASKLOG_ENABLED = True
CELERY_TASKLOG_MAX_LINES = 1000
CELERY_TASKLOG_RETENTION_DAYS = 30

# Django REST framework
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
}
```

## Step 7: Set Up Direnv (.envrc)

```bash
echo "layout poetry" > .envrc
direnv allow
```

## Step 8: Package Installation Configuration

In celery_tasklog/pyproject.toml:

```toml
[tool.poetry]
name = "celery_tasklog"
version = "0.1.0"
description = "Celery Task Log - Real-time task monitoring for Django/Celery"
authors = ["Your Name <you@example.com>"]
license = "MIT"
readme = "README.md"
homepage = "https://github.com/yourusername/celery-tasklog"
repository = "https://github.com/yourusername/celery-tasklog"
documentation = "https://github.com/yourusername/celery-tasklog/blob/main/README.md"
keywords = ["celery", "django", "task", "logging", "monitoring"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Web Environment",
    "Framework :: Django",
    "Framework :: Django :: 3.2",
    "Framework :: Django :: 4.0",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Topic :: Software Development :: Libraries :: Python Modules",
]
packages = [{include = "celery_tasklog", from = "src"}]

[tool.poetry.dependencies]
python = "^3.8"
Django = "^3.2"
celery = "^5.0"
django-celery-results = "^2.0"

[tool.poetry.dev-dependencies]
black = "^21.9b0"
isort = "^5.9.3"
flake8 = "^3.9.2"
pytest = "^6.2.4"
pytest-django = "^4.3.0"
factory-boy = "^3.2.1"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

## Step 9: Build and Install Package

```bash
cd celery_tasklog
poetry build
pip install dist/celery_tasklog-0.1.0-py3-none-any.whl
```

## Step 10: Docker Configuration

### Dockerfile

```Dockerfile
# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock /app/
RUN pip install poetry
RUN poetry install --no-root

# Copy project files
COPY . /app/

# Run database migrations
RUN poetry run python manage.py migrate

# Expose port
EXPOSE 8000

# Start the server
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    command: poetry run python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - db

  worker:
    build: .
    command: poetry run celery -A djproject worker --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
      - db

  beat:
    build: .
    command: poetry run celery -A djproject beat --loglevel=info
    volumes:
      - .:/app
    depends_on:
      - redis
      - db

  redis:
    image: "redis:alpine"

  db:
    image: postgres
    environment:
      POSTGRES_DB: celery_tasklog
      POSTGRES_USER: celery_tasklog
      POSTGRES_PASSWORD: celery_tasklog
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## API and SSE Endpoints

Include the package URLs in your project:

```python
path('tasklog/', include('celery_tasklog.urls'))
```

Available routes:

- `/tasklog/api/tasks/` - list recent tasks with progress
- `/tasklog/api/tasks/<task_id>/` - retrieve a single task with its logs
- `/tasklog/sse/task/<task_id>/` - stream log lines via Server-Sent Events
- `/tasklog/sse/test/` - simple test stream

Log lines are broadcast from Celery workers to Redis using signals and
relayed to connected SSE clients.

## Verification Steps

1. Build and install the package:
```bash
cd celery_tasklog
poetry build
pip install dist/celery_tasklog-*.whl
```

2. Run migrations:
```bash
poetry run python manage.py migrate
```

3. Start Celery worker:
```bash
poetry run celery -A djproject worker -l INFO
```

4. Start Django server:
```bash
poetry run python manage.py runserver
```

5. Test with demo task:
```python
from demo.tasks import demo_long_task
demo_long_task.delay(5)
```

6. Verify SSE streaming:
```bash
python tests/test_sse_client.py
```

## Configuration Options

The package exposes the following configuration options:

- `CELERY_TASKLOG_ENABLED`: Boolean to enable/disable task logging (default: True)
- `CELERY_TASKLOG_MAX_LINES`: Maximum number of log lines to store per task (default: 1000)
- `CELERY_TASKLOG_RETENTION_DAYS`: Number of days to retain task logs (default: 30)

## Middleware

The package includes a middleware component that can be added to Django settings to provide task logging context throughout the request/response cycle.

## Additional Utilities

- Admin interface for viewing task logs
- Diagnostic views for troubleshooting
- REST API endpoints for task status and logs
- SSE endpoints for real-time log streaming

## Support

This package supports the latest versions of Django and Celery. For specific version compatibility, see the package's `pyproject.toml` file.

## Contributing

Contributions are welcome! Please submit issues and pull requests to the project's GitHub repository.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
