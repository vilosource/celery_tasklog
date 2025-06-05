# celery_tasklog

`celery_tasklog` provides a Django application that records stdout/stderr from Celery tasks in the database so logs can be streamed to the browser. The package is packaged with Poetry and can be used in any project.

## Features

* Database model `TaskLogLine` to persist task output.
* Middleware and admin integration.
* Utilities such as cleanup commands and diagnostic views.

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

For more details see the full [CeleryTaskLogSpec](docs/CeleryTaskLogSpec.md).
