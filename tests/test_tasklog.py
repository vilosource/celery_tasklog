import sys
import os
import pathlib
import pytest

# Ensure the package src directory is on the Python path when tests run
ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_PATH = str(ROOT / "celery_tasklog")
sys.path.insert(0, BASE_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djproject.settings")
import django
from django.conf import settings

settings.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

django.setup()

import importlib

celery_pkg = importlib.import_module("src.celery_tasklog")
sys.modules["celery_tasklog"] = celery_pkg

from celery_tasklog.tasks import capture_output, TerminalLoggingTask
from celery_tasklog.models import TaskLogLine


@pytest.mark.django_db
def test_capture_output_writes_to_db():
    task_id = "capture-test"
    with capture_output(task_id):
        print("hello")
        print("oops", file=sys.stderr)

    logs = list(TaskLogLine.objects.filter(task_id=task_id).order_by("id"))
    assert len(logs) == 2
    assert logs[0].stream == "stdout"
    assert logs[0].message == "hello"
    assert logs[1].stream == "stderr"
    assert logs[1].message == "oops"


@pytest.mark.django_db
def test_terminal_logging_task_records_output():
    class SampleTask(TerminalLoggingTask):
        name = "sample"

        def run(self, x, y):
            print(f"adding {x} and {y}")
            return x + y

    task = SampleTask()
    with capture_output("task-001"):
        result = task.run(2, 3)
    assert result == 5

    messages = list(TaskLogLine.objects.filter(task_id="task-001").values_list("message", flat=True))
    assert "adding 2 and 3" in messages[0]
