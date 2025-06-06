#!/usr/bin/env python3
"""Manual SSE client used for development troubleshooting.

This module is not intended to run as part of the automated test suite. When
executed directly it will connect to the SSE endpoint and print received events
to stdout. Pytest skips this file by default so it can live inside ``tests/``
without causing failures.
"""

import json
import os
import requests

import pytest


pytest.skip("manual utility, not an automated test", allow_module_level=True)


def sse_client(task_id: str) -> None:
    """Stream events for ``task_id`` and print them."""
    base_url = os.environ.get("SSE_BASE_URL", "http://localhost:8000")
    headers = {"Accept": "text/event-stream"}
    response = requests.get(
        f"{base_url}/tasklog/sse/task/{task_id}/",
        headers=headers,
        stream=True,
    )

    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(response.text)
        return

    print("Connection established, listening for events...")

    for line in response.iter_lines():
        if line and line.startswith(b"data: "):
            data_str = line[6:].decode("utf-8")
            try:
                data = json.loads(data_str)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                print(f"Could not parse JSON: {data_str}")


if __name__ == "__main__":
    task_id = input("Enter the task ID to monitor: ")
    try:
        sse_client(task_id)
    except KeyboardInterrupt:
        print("\nExiting SSE test client")

