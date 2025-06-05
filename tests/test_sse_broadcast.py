import asyncio
import json
import pytest
from django.urls import reverse
from django.test import Client
from celery import shared_task

# Simple dummy task for testing
asyncio_task_ran = False

@shared_task
def simple_task():
    global asyncio_task_ran
    print("simple task running")
    asyncio_task_ran = True

@pytest.mark.django_db
@pytest.mark.asyncio
async def test_sse_broadcast(live_server):
    task_id = simple_task.delay().id
    await asyncio.sleep(1)  # allow task to start

    url = f"{live_server.url}/tasklog/sse/task/{task_id}/"
    client = Client()
    response = client.get(url, HTTP_ACCEPT="text/event-stream")

    # Consume a few events from the generator
    iterator = response.streaming_content
    messages = []
    for _ in range(3):
        event = next(iterator).decode()
        if event.startswith("data: "):
            messages.append(json.loads(event[6:].strip()))

    assert any(m.get("type") == "connected" for m in messages)
