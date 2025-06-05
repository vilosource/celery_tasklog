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


@shared_task(bind=True, base=TerminalLoggingTask, name='celery_tasklog.tasks.timed_print_task')
def timed_print_task(self):
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
