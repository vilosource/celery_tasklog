# celery_tasklog

`celery_tasklog` is a Django application that **captures and stores stdout/stderr output from Celery tasks in a database**, enabling real-time viewing of task logs through a web browser interface. This transforms ephemeral console logs into persistent, web-accessible database records.

## What It Does

### Core Functionality
- **Database Logging**: Intercepts and stores all stdout/stderr output from Celery tasks using a `TaskLogLine` model
- **Real-time Monitoring**: View task execution logs in real-time through web interface
- **Output Capture**: Uses a sophisticated context manager system to redirect task output to the database
- **Web Interface**: Browse, search, and view task logs through Django views and admin interface

### Key Components

#### 1. **Output Capture System**
- `DBLogWriter`: Intercepts stdout/stderr and buffers output for database storage
- `capture_output`: Context manager that redirects task output to the database
- `TerminalLoggingTask`: Base task class that automatically captures output for any task

#### 2. **Database Model**
The `TaskLogLine` model stores:
- `task_id`: Links logs to specific Celery tasks
- `timestamp`: When the log line was created
- `stream`: Whether it's stdout or stderr output  
- `message`: The actual log content

#### 3. **Web Interface**
- **Task Log View**: Display all log lines for a specific task ID in chronological order
- **Diagnostic View**: Health check page to verify the system is working
- **Django Admin Integration**: Browse, search, and manage task logs

#### 4. **Example Task Implementation**
Includes `timed_print_task` demonstrating:
- Progress tracking with `self.update_state()`
- Automatic output capture via `TerminalLoggingTask` base class
- Error handling with database logging
- Real-time log streaming to database

## Features

* **Database model `TaskLogLine`** to persist task output with timestamps and stream identification
* **Automatic output capture** using context managers and custom task base classes  
* **Web interface** for viewing and monitoring task execution in real-time
* **Django admin integration** for log management and searching
* **Error handling** with automatic stderr capture and logging
* **Configurable retention** and line limits for log management
* **Progress tracking** integration with Celery's state system

## Use Cases

This is particularly useful for:
- **Debugging Celery tasks** by viewing their output in real-time without server access
- **Monitoring long-running tasks** and their progress through web dashboards
- **Auditing task execution** with persistent log storage and timestamps
- **Troubleshooting production issues** with comprehensive error capture
- **Creating task monitoring dashboards** with real-time log streaming

Configuration options are exposed through environment variables as described in the [specification](docs/CeleryTaskLogSpec.md):

- `CELERY_TASKLOG_ENABLED` – enable or disable logging (default `True`).
- `CELERY_TASKLOG_MAX_LINES` – maximum log lines stored per task (default `1000`).
- `CELERY_TASKLOG_RETENTION_DAYS` – log retention in days (default `30`).

## Usage in your project

1. Install the package:
   ```bash
   pip install celery_tasklog
   ```
2. Add `celery_tasklog` to `INSTALLED_APPS` and include `CeleryTaskLogMiddleware` in your middleware list.
3. Run database migrations:
   ```bash
   python manage.py migrate
   ```
4. Start the Celery worker alongside your Django server. Example commands can be found in the [verification steps](docs/CeleryTaskLogSpec.md).

## Docker deployment

A Dockerfile is provided following the structure from the specification:

```Dockerfile
# Use the official Python image from the Docker Hub
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
```
[...]

The docker-compose file builds the image, runs the web application, Celery worker, beat scheduler, Flower dashboard and a PostgreSQL database:

```yaml
version: '3.8'
services:
  web:
    build: .
    command: poetry run gunicorn djproject.wsgi:application -b 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
      - worker
  worker:
    build: .
    command: poetry run celery -A djproject worker -l info
```
(see `docker-compose.yml` for the full configuration).

Environment variables are loaded from `.env`, keeping the project [12‑factor](https://12factor.net/) compliant.

## Running locally

1. Create a `.env` file with at least the PostgreSQL credentials used in `docker-compose.yml`.
2. Build and start the stack:
   ```bash
   docker compose up --build
   ```
3. Access Flower at [http://localhost:5555](http://localhost:5555) and the Django site at [http://localhost:8000](http://localhost:8000).

## Linting

Run `flake8` to check coding style:

```bash
poetry run flake8
```

## Testing SSE

With the stack running and a task executing, you can monitor log events using the provided client:

```bash
python tests/test_sse_client.py
```

Enter the task ID when prompted to see events streamed from the server. Full automated tests are executed with `pytest`:

```bash
poetry run pytest
```

For more details see the full [CeleryTaskLogSpec](docs/CeleryTaskLogSpec.md).
