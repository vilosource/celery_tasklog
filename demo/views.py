from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response


def demo_home(request):
    """Demo home page with task trigger form and task list."""
    return render(request, "demo/demo_home.html")


def demo_task_detail(request, task_id):
    """Demo task detail page with real-time logs."""
    return render(request, "demo/demo_task_detail.html", {"task_id": task_id})


@api_view(["POST"])
def trigger_demo_task(request):
    """Endpoint to start one of the demo tasks."""
    try:
        from demo.tasks import demo_long_task, demo_failing_task, demo_quick_task
    except ImportError:
        return Response(
            {
                "error": "Demo tasks not available. Make sure the demo app is installed and configured."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    task_type = request.data.get("task_type", "long")
    duration = request.data.get("duration", 60)

    try:
        duration = int(duration)
        if duration < 1 or duration > 300:
            duration = 60
    except (ValueError, TypeError):
        duration = 60

    if task_type == "failing":
        result = demo_failing_task.delay()
        message = "Demo failing task started"
    elif task_type == "quick":
        result = demo_quick_task.delay()
        message = "Demo quick task started"
    else:
        result = demo_long_task.delay(duration)
        message = f"Demo long task started with duration {duration} seconds"

    return Response(
        {
            "task_id": result.id,
            "task_type": task_type,
            "duration": duration if task_type == "long" else None,
            "message": message,
        }
    )

