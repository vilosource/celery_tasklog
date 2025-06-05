from celery import shared_task
import time
import random
from datetime import datetime
import pytz

# Import celery_tasklog features
from celery_tasklog.tasks import TerminalLoggingTask, capture_output
from celery_tasklog.models import TaskLogLine


@shared_task(base=TerminalLoggingTask, bind=True)
def demo_long_task(self, duration=60):
    """
    Demo task that runs for a specified duration and outputs random messages.
    This demonstrates how to use TerminalLoggingTask to capture stdout/stderr.
    
    Args:
        duration (int): How long the task should run in seconds (default: 60)
    """
    print(f"Starting demo task that will run for {duration} seconds")
    print(f"Task ID: {self.request.id}")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 50)
    
    start_time = time.time()
    step = 0
    
    while time.time() - start_time < duration:
        step += 1
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        
        # Random messages to stdout
        messages = [
            f"Step {step}: Processing data batch...",
            f"Step {step}: Analyzing patterns in dataset...",
            f"Step {step}: Running machine learning algorithm...",
            f"Step {step}: Optimizing parameters...",
            f"Step {step}: Validating results...",
            f"Step {step}: Generating reports...",
            f"Step {step}: Cleaning up temporary files...",
            f"Step {step}: Backing up progress...",
        ]
        
        print(f"[{elapsed:.1f}s] {random.choice(messages)}")
        
        # Occasionally print to stderr for demo purposes
        if random.random() < 0.15:  # 15% chance
            import sys
            print(f"[WARNING] Step {step}: Minor issue detected, continuing...", file=sys.stderr)
        
        # Update task progress
        progress = min(int((elapsed / duration) * 100), 100)
        self.update_state(
            state='PROGRESS',
            meta={
                'current': step,
                'total': duration,
                'progress': progress,
                'elapsed': elapsed,
                'remaining': remaining,
                'status': f'Processing step {step}...'
            }
        )
        
        # Random sleep between 0.5 and 2 seconds
        sleep_time = random.uniform(0.5, 2.0)
        time.sleep(sleep_time)
    
    print("=" * 50)
    print(f"Task completed successfully!")
    print(f"Total steps: {step}")
    print(f"Actual duration: {time.time() - start_time:.1f} seconds")
    print(f"Finished at: {datetime.now().isoformat()}")
    
    return {
        'status': 'completed',
        'steps': step,
        'duration': time.time() - start_time,
        'message': f'Demo task completed successfully with {step} steps'
    }


@shared_task(base=TerminalLoggingTask, bind=True)
def demo_failing_task(self):
    """
    Demo task that fails after some processing to demonstrate error handling.
    """
    print("Starting demo failing task...")
    print("This task will fail after some processing")
    
    for i in range(5):
        print(f"Processing step {i+1}/5...")
        time.sleep(1)
        
        if i == 3:
            import sys
            print("Error detected in step 4!", file=sys.stderr)
    
    # Simulate failure
    print("Critical error occurred!")
    raise Exception("Demo task failed as expected")


@shared_task(base=TerminalLoggingTask, bind=True) 
def demo_quick_task(self):
    """
    Demo task that completes quickly for testing.
    """
    print("Starting quick demo task...")
    
    for i in range(3):
        print(f"Quick step {i+1}/3")
        time.sleep(0.5)
    
    print("Quick task completed!")
    return {'status': 'completed', 'message': 'Quick demo task finished'}

