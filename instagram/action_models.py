"""Models for the outbound action engine.

Defines ``ActionExecution`` which tracks each outbound Instagram action.
"""

import uuid
from django.db import models
from django.utils import timezone

class ActionExecution(models.Model):
    """Tracks a single outbound Instagram action.

    ``execution_key`` provides idempotency – duplicate submissions with the same
    payload resolve to the same record.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
        DEAD_LETTER = 'dead_letter', 'Dead Letter'

    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Assuming WorkflowExecution model lives in workflow_bridge app
    # WorkflowExecution is defined in instagram/event_models.py
    workflow_execution = models.ForeignKey(
        'instagram.WorkflowExecution',
        on_delete=models.SET_NULL,
        related_name='action_executions',
        null=True,
        blank=True,
    )
    action_type = models.CharField(max_length=32)
    instagram_account = models.ForeignKey('instagram.InstagramAccount', on_delete=models.CASCADE)
    recipient = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    request_payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    execution_key = models.CharField(max_length=64, unique=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.action_type} - {self.execution_id}"
