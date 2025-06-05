from django.shortcuts import render
from .tasks import long_running_task


def demo_view(request):
    if request.method == 'POST':
        seconds = int(request.POST.get('seconds', 5))
        long_running_task.delay(seconds)
        return render(request, 'demo/demo_complete.html', {'seconds': seconds})
    return render(request, 'demo/demo_form.html')
