from django.db import models


class TaskLogLine(models.Model):
    task_id = models.CharField(max_length=255, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    stream = models.CharField(max_length=10, choices=[("stdout", "stdout"), ("stderr", "stderr")])
    message = models.TextField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.timestamp} [{self.stream}] {self.message}"
