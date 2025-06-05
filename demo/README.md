# Celery TaskLog Demo

This demo app showcases the functionality of the `celery_tasklog` Django app, which provides real-time logging capabilities for Celery tasks.

## Features Demonstrated

### 1. Task Logging
- **TerminalLoggingTask Base Class**: All demo tasks inherit from this base class
- **Automatic Capture**: All `stdout` and `stderr` output is captured automatically
- **Database Storage**: Logs are stored in the database via Django signals
- **Real-time Updates**: New log entries trigger immediate SSE broadcasts

### 2. Demo Tasks

#### Long Task (`demo_long_task`)
- Configurable duration (1-300 seconds, default: 60)
- Simulates data processing with random stdout/stderr output
- Updates progress state throughout execution
- Demonstrates real-time logging over extended periods

#### Quick Task (`demo_quick_task`) 
- Runs for approximately 3 seconds
- Quick demonstration of the logging system
- Ideal for testing without waiting

#### Failing Task (`demo_failing_task`)
- Deliberately fails after some processing
- Demonstrates error handling and stderr capture
- Shows how failures are logged and displayed

### 3. Real-time Features

#### Server-Sent Events (SSE)
- Live log streaming without page refresh
- Automatic reconnection on connection loss
- Keepalive messages to maintain connection
- Color-coded stdout (white) vs stderr (red) display

#### API Endpoints
- `GET /demo/api/tasks/` - List all tasks with status
- `GET /demo/api/tasks/{task_id}/` - Get task details and logs  
- `POST /demo/api/trigger-demo/` - Start new demo tasks
- `GET /demo/sse/task/{task_id}/` - SSE stream for live logs

### 4. User Interface

#### Home Page (`/demo/`)
- Task trigger form with options for different task types
- Live task list with status and progress indicators
- Auto-refresh every 5 seconds
- Direct links to individual task log viewers

#### Task Detail Page (`/demo/task/{task_id}/`)
- Real-time log viewer with auto-scroll
- Connection status indicator
- Task progress and status display
- Log download functionality
- Manual log refresh capabilities

## How It Works

### 1. Task Execution Flow
```
User triggers task → Celery worker picks up task → TerminalLoggingTask captures output → 
Logs stored in database → Django signals broadcast → SSE pushes to browser → UI updates
```

### 2. Architecture Components

#### Backend (Django + Celery)
- **TerminalLoggingTask**: Custom Celery task base class
- **DBLogWriter**: Captures stdout/stderr and writes to database
- **TaskLogLine Model**: Stores individual log lines with timestamps
- **Django Signals**: Broadcast new logs to SSE connections
- **DRF ViewSets**: Provide REST API for task management

#### Frontend (Bootstrap + JavaScript)
- **Server-Sent Events**: Receive real-time log updates
- **Fetch API**: Communicate with REST endpoints  
- **Bootstrap**: Responsive, professional UI components
- **Auto-scroll**: Automatically follow latest log entries

### 3. Signal-Based Broadcasting
When new TaskLogLine objects are created, Django's `post_save` signal:
1. Formats the log entry as JSON
2. Pushes to all SSE connections for that task
3. Handles connection cleanup and error recovery

## Usage Examples

### Basic Task Creation
```python
from celery_tasklog.tasks import TerminalLoggingTask
from celery import shared_task

@shared_task(base=TerminalLoggingTask, bind=True)
def my_custom_task(self):
    print("This will be captured and logged!")
    # Task logic here
    print("Task completed successfully")
```

### API Usage
```javascript
// Start a task
const response = await fetch('/demo/api/trigger-demo/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({task_type: 'long', duration: 120})
});

// Monitor with SSE
const eventSource = new EventSource(`/demo/sse/task/${taskId}/`);
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'new_log') {
        console.log(`[${data.stream}] ${data.message}`);
    }
};
```

## Development Notes

### Environment Setup
- Docker Compose with PostgreSQL, Redis, Django, and Celery
- Environment variables in `.env` file
- Volume mounting for live development

### Key Files
- `demo/tasks.py` - Demo task implementations
- `demo/views.py` - API endpoints and SSE streaming
- `demo/templates/` - Bootstrap UI templates
- `celery_tasklog/tasks.py` - Core TerminalLoggingTask class
- `celery_tasklog/models.py` - TaskLogLine database model

This demo provides a complete example of how to integrate `celery_tasklog` into your Django application for real-time task monitoring and logging.
