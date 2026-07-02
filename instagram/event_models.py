from django.db import models
import uuid
from django.utils import timezone

class WorkflowEvent(models.Model):
    """Standardized representation of an incoming Instagram event (comment, DM, etc.)."""
    EVENT_TYPE_CHOICES = [
        ('comment', 'Comment'),
        ('dm', 'Direct Message'),
        ('other', 'Other'),
    ]
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    source = models.CharField(max_length=30)  # e.g., "instagram"
    account = models.ForeignKey('instagram.InstagramAccount', on_delete=models.CASCADE, related_name='workflow_events')
    raw_payload = models.JSONField()
    received_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.source}:{self.event_type}:{self.event_id}"

class WorkflowExecution(models.Model):
    """Record of a workflow execution triggered by a WorkflowEvent."""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    event = models.ForeignKey(WorkflowEvent, on_delete=models.CASCADE, related_name='executions')
    workflow = models.ForeignKey('automation.AutomationWorkflow', on_delete=models.CASCADE, related_name='event_executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('event', 'workflow')

    def __str__(self):
        return f"Exec {self.id} for {self.workflow.name} ({self.status})"
