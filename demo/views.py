from django.shortcuts import render


def demo_home(request):
    """Demo home page with task trigger form and task list"""
    return render(request, 'demo/demo_home.html')


def demo_task_detail(request, task_id):
    """Demo task detail page with real-time logs"""
    return render(request, 'demo/demo_task_detail.html', {'task_id': task_id})