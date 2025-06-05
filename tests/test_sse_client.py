#!/usr/bin/env python3
import json
import os
import requests
import time

def test_sse_connection(task_id):
    """
    Test SSE connection for a specific task ID
    """
    print(f"Testing SSE connection for task {task_id}")
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
    
    # Listen for events
    for line in response.iter_lines():
        if line:
            # Remove "data: " prefix and parse JSON
            if line.startswith(b'data: '):
                data_str = line[6:].decode('utf-8')
                try:
                    data = json.loads(data_str)
                    print(f"Received event: {json.dumps(data, indent=2)}")
                    
                    # If it's a keepalive message, print simpler output
                    if data.get('type') == 'keepalive':
                        print("(Keepalive received)")
                except json.JSONDecodeError:
                    print(f"Could not parse JSON: {data_str}")

if __name__ == "__main__":
    # Get the task ID from user input
    task_id = input("Enter the task ID to monitor: ")
    
    try:
        test_sse_connection(task_id)
    except KeyboardInterrupt:
        print("\nExiting SSE test client")

