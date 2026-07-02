"""queue_manager.py

Thin adapter that enqueues an ActionExecution for async processing via Celery.
If CELERY_TASK_ALWAYS_EAGER is True (test/dev), the task runs in-process.
"""

import logging

logger = logging.getLogger(__name__)


def enqueue_action(action_execution_id):
    """Enqueue an action execution task by its primary key.

    Avoids a circular import by importing the task lazily.
    """
    from instagram.action_tasks import execute_action_task  # defined in action_tasks.py
    logger.debug(f"Enqueuing action execution {action_execution_id}")
    execute_action_task.delay(action_execution_id)
