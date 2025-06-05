import sys
from contextlib import contextmanager

from celery import Task
from .models import TaskLogLine


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
