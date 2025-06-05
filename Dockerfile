FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml* poetry.lock* ./
RUN pip install --no-cache-dir poetry \
    && poetry install --no-interaction --no-ansi --no-root

COPY . /app/

RUN poetry run python manage.py collectstatic --noinput 2>/dev/null || true

CMD ["poetry", "run", "gunicorn", "djproject.wsgi:application", "-b", "0.0.0.0:8000"]
