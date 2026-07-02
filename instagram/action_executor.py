"""action_executor.py

Core orchestrator for outbound Instagram actions.

Usage example:
    from instagram.action_executor import ActionExecutor
    executor = ActionExecutor()
    executor.submit(
        action_type='SEND_DM',
        payload={'account_id': 1, 'recipient_id': 'user123', 'text': 'Hello!'},
        workflow_execution_id=workflow_execution_id,
    )
"""

import json
import hashlib
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from .action_models import ActionExecution
from .models import InstagramAccount
from .queue_manager import enqueue_action
from .exceptions import ValidationError

class ActionExecutor:
    """Facade for submitting outbound actions.

    It validates the payload, creates an idempotent ``ActionExecution`` record,
    and enqueues the task for asynchronous processing.
    """

    # Required fields per action type (simple validation; can be extended with pydantic).
    _required_fields = {
        'SEND_DM': ['account_id', 'recipient_id', 'text'],
        'REPLY_DM': ['account_id', 'thread_id', 'text'],
        'REPLY_COMMENT': ['account_id', 'comment_id', 'text'],
        'MESSAGE_REACTION': ['account_id', 'message_id', 'reaction'],
    }

    def _validate(self, action_type: str, payload: Dict[str, Any]) -> None:
        required = self._required_fields.get(action_type)
        if required is None:
            # Unknown actions are accepted; they will be handled as UNKNOWN_ACTION downstream.
            return
        missing = [k for k in required if k not in payload]
        
        # Special case for SEND_DM: allow recipient_username instead of recipient_id
        if action_type == 'SEND_DM' and 'recipient_id' in missing and 'recipient_username' in payload:
            missing.remove('recipient_id')
            
        if missing:
            raise ValidationError(f"Missing fields for {action_type}: {', '.join(missing)}")

    def _make_execution_key(self, action_type: str, payload: Dict[str, Any]) -> str:
        # Deterministic idempotency key based on type and payload content.
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        raw = f"{action_type}:{payload_json}".encode()
        return hashlib.sha256(raw).hexdigest()

    def submit(self, action_type: str, payload: Dict[str, Any], workflow_execution_id) -> ActionExecution:
        # Validate payload schema.
        self._validate(action_type, payload)

        # Resolve InstagramAccount.
        account_id = payload.get('account_id')
        try:
            account = InstagramAccount.objects.get(pk=account_id)
        except InstagramAccount.DoesNotExist as exc:
            raise ValidationError(f"InstagramAccount {account_id} not found") from exc

        execution_key = self._make_execution_key(action_type, payload)

        with transaction.atomic():
            action_execution, created = ActionExecution.objects.get_or_create(
                execution_key=execution_key,
                defaults={
                    'workflow_execution_id': workflow_execution_id,  # nullable FK — pass None or a PK
                    'action_type': action_type,
                    'instagram_account': account,
                    'recipient': (
                        payload.get('recipient_id')
                        or payload.get('recipient_username')
                        or payload.get('thread_id')
                        or payload.get('comment_id')
                    ),
                    'status': ActionExecution.Status.PENDING,
                    'request_payload': payload,
                    'attempt_count': 0,
                    'created_at': timezone.now(),
                },
            )

        # If already succeeded, return early (idempotency).
        if not created and action_execution.status == ActionExecution.Status.SUCCESS:
            return action_execution

        # Enqueue for async processing.
        # Primary key is execution_id (UUID), not .id
        enqueue_action(str(action_execution.execution_id))
        return action_execution
