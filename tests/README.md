# Test Suite

The automated tests cover the core functionality of the `celery_tasklog` app.
They verify that log output is captured in the database and demonstrate how the
TerminalLoggingTask base class works. Tests that rely on an external broker and
running Celery worker are skipped by default.

Run tests with:

```bash
pytest
```
