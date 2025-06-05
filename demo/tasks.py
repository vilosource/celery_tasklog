from celery import shared_task
import time

@shared_task(bind=True)
def long_running_task(self, seconds: int):
    for i in range(seconds):
        print(f"Processing step {i+1}/{seconds}")
        time.sleep(1)
    return f"Completed {seconds} second task"
