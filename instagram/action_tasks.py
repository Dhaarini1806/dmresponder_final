"""action_tasks.py

Celery task that processes a single ActionExecution (outbound Instagram action).
Uses instagrapi to send real DMs, reply to DMs, and reply to comments.
"""

import logging
from celery import shared_task
from django.utils import timezone
from instagrapi.exceptions import (
    BadPassword, ChallengeRequired, TwoFactorRequired, 
    FeedbackRequired, PleaseWaitFewMinutes, LoginRequired,
    UserNotFound, MediaNotFound
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


@shared_task(bind=True, max_retries=MAX_ATTEMPTS)
def execute_action_task(self, action_execution_id):
    """
    Executes a single outbound Instagram action.

    Lifecycle:
      PENDING → RUNNING → SUCCESS | FAILED | DEAD_LETTER
    """
    from instagram.action_models import ActionExecution
    from instagram.models import InstagramAccount

    try:
        action_exec = ActionExecution.objects.get(execution_id=action_execution_id)
    except ActionExecution.DoesNotExist:
        logger.error(f"ActionExecution {action_execution_id} not found.")
        return

    # Mark as running
    action_exec.status = ActionExecution.Status.RUNNING
    action_exec.started_at = timezone.now()
    action_exec.attempt_count += 1
    action_exec.save(update_fields=["status", "started_at", "attempt_count"])

    try:
        result = _dispatch_action(action_exec)
        action_exec.status = ActionExecution.Status.SUCCESS
        action_exec.response_payload = result
        action_exec.completed_at = timezone.now()
        action_exec.save(update_fields=["status", "response_payload", "completed_at"])
        logger.info(f"Action {action_exec.action_type} ({action_execution_id}) succeeded.")
        return result

    except Exception as exc:
        # Check if error indicates session/authentication failure (like BadPassword, LoginRequired, or custom 'Session expired')
        is_auth_failure = False
        exc_str = str(exc).lower()
        if isinstance(exc, (BadPassword, LoginRequired)) or "session expired" in exc_str or "login_required" in exc_str or "bad_password" in exc_str:
            is_auth_failure = True
            
        logger.warning(
            f"Action {action_exec.action_type} ({action_execution_id}) failed "
            f"(attempt {action_exec.attempt_count}): {exc}"
        )
        
        if is_auth_failure:
            # Mark the account as disconnected and fail the action permanently (no retries)
            account = action_exec.instagram_account
            if account:
                logger.warning(f"Session expired or auth failure for {account.username} during action. Disconnecting account.")
                account.status = 'disconnected'
                account.save()
            
            action_exec.status = ActionExecution.Status.DEAD_LETTER
            action_exec.error_message = f"Authentication failure: {exc}"
            action_exec.completed_at = timezone.now()
            action_exec.save(update_fields=["status", "error_message", "completed_at"])
            return
            
        if action_exec.attempt_count >= MAX_ATTEMPTS:
            action_exec.status = ActionExecution.Status.DEAD_LETTER
            action_exec.error_message = str(exc)
            action_exec.completed_at = timezone.now()
            action_exec.save(update_fields=["status", "error_message", "completed_at"])
            logger.error(
                f"Action {action_exec.action_type} ({action_execution_id}) moved to Dead Letter Queue."
            )
            return
        else:
            action_exec.status = ActionExecution.Status.FAILED
            action_exec.error_message = str(exc)
            action_exec.save(update_fields=["status", "error_message"])
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _dispatch_action(action_exec):
    """Route to the correct handler by action type."""
    handlers = {
        "SEND_DM": _handle_send_dm,
        "REPLY_DM": _handle_reply_dm,
        "REPLY_COMMENT": _handle_reply_comment,
    }
    handler = handlers.get(action_exec.action_type)
    if handler is None:
        raise NotImplementedError(f"No handler for action type: {action_exec.action_type}")
    return handler(action_exec)


def _handle_send_dm(action_exec):
    """
    Send a direct message to a user.
    
    Payload: {
        'account_id': <int>,  # InstagramAccount.pk
        'recipient_id': <str>,  # Instagram user ID
        'text': <str>  # Message text
    }
    """
    from instagram.services import InstagramService
    from instagram.exceptions import InstagramException
    
    payload = action_exec.request_payload
    account = action_exec.instagram_account
    recipient_id = payload.get('recipient_id')
    recipient_username = payload.get('recipient_username')
    text = payload.get('text', '')
    
    if not (recipient_id or recipient_username) or not text:
        raise ValueError(f"Missing recipient_id/username or text in payload: {payload}")
    
    try:
        # Get authenticated instagrapi client
        client = InstagramService.get_instagram_client(account)
        
        # Resolve username to user_id if needed
        if not recipient_id and recipient_username:
            recipient_id = client.user_id_from_username(recipient_username)
            logger.info(f"[SEND_DM] Resolved username {recipient_username} to ID {recipient_id}")
        
        # Send the direct message
        # recipient_id is Instagram user ID (integer or string)
        result = client.direct_send(text, user_ids=[int(recipient_id)])
        
        logger.info(
            f"[SEND_DM] Successfully sent DM from {account.username} "
            f"to user {recipient_id}: {text[:50]}..."
        )
        
        return {
            "status": "sent",
            "platform": "instagram",
            "recipient_id": recipient_id,
            "message": text,
            "thread_id": result.get('thread_id') if isinstance(result, dict) else None
        }
        
    except UserNotFound:
        logger.error(f"[SEND_DM] User {recipient_id} not found")
        raise InstagramException(f"Instagram user {recipient_id} not found")
    except (BadPassword, LoginRequired):
        logger.error(f"[SEND_DM] Session invalid for {account.username}, attempting refresh")
        raise InstagramException(f"Session expired for {account.username}")
    except PleaseWaitFewMinutes as e:
        logger.warning(f"[SEND_DM] Rate limited: {e}")
        raise InstagramException(f"Rate limited by Instagram: {e}")
    except Exception as e:
        logger.error(f"[SEND_DM] Error sending DM from {account.username} to {recipient_id}: {e}")
        raise


def _handle_reply_dm(action_exec):
    """
    Reply to a direct message thread.
    
    Payload: {
        'account_id': <int>,  # InstagramAccount.pk
        'thread_id': <str>,  # Direct message thread ID
        'text': <str>  # Reply text
    }
    """
    from instagram.services import InstagramService
    from instagram.exceptions import InstagramException
    
    payload = action_exec.request_payload
    account = action_exec.instagram_account
    thread_id = payload.get('thread_id')
    text = payload.get('text', '')
    
    if not thread_id or not text:
        raise ValueError(f"Missing thread_id or text in payload: {payload}")
    
    try:
        # Get authenticated instagrapi client
        client = InstagramService.get_instagram_client(account)
        
        # Send message to thread
        result = client.direct_send(text, thread_ids=[int(thread_id)])
        
        logger.info(
            f"[REPLY_DM] Successfully replied in thread {thread_id} "
            f"from {account.username}: {text[:50]}..."
        )
        
        return {
            "status": "replied",
            "platform": "instagram",
            "thread_id": thread_id,
            "message": text
        }
        
    except (BadPassword, LoginRequired):
        logger.error(f"[REPLY_DM] Session invalid for {account.username}")
        raise InstagramException(f"Session expired for {account.username}")
    except PleaseWaitFewMinutes as e:
        logger.warning(f"[REPLY_DM] Rate limited: {e}")
        raise InstagramException(f"Rate limited by Instagram: {e}")
    except Exception as e:
        logger.error(f"[REPLY_DM] Error replying in thread {thread_id} from {account.username}: {e}")
        raise


def _handle_reply_comment(action_exec):
    """
    Reply to a comment on a media post.
    
    Payload: {
        'account_id': <int>,  # InstagramAccount.pk
        'comment_id': <str>,  # Comment ID
        'text': <str>  # Reply text
    }
    """
    from instagram.services import InstagramService
    from instagram.exceptions import InstagramException
    
    payload = action_exec.request_payload
    account = action_exec.instagram_account
    comment_id = payload.get('comment_id')
    text = payload.get('text', '')
    
    if not comment_id or not text:
        raise ValueError(f"Missing comment_id or text in payload: {payload}")
    
    try:
        # Get authenticated instagrapi client
        client = InstagramService.get_instagram_client(account)
        
        # Reply to the comment
        result = client.comment_reply(text, comment_id)
        
        logger.info(
            f"[REPLY_COMMENT] Successfully replied to comment {comment_id} "
            f"from {account.username}: {text[:50]}..."
        )
        
        return {
            "status": "replied",
            "platform": "instagram",
            "comment_id": comment_id,
            "message": text,
            "reply_id": result if isinstance(result, (str, int)) else None
        }
        
    except MediaNotFound:
        logger.error(f"[REPLY_COMMENT] Comment {comment_id} or media not found")
        raise InstagramException(f"Comment {comment_id} not found")
    except (BadPassword, LoginRequired):
        logger.error(f"[REPLY_COMMENT] Session invalid for {account.username}")
        raise InstagramException(f"Session expired for {account.username}")
    except PleaseWaitFewMinutes as e:
        logger.warning(f"[REPLY_COMMENT] Rate limited: {e}")
        raise InstagramException(f"Rate limited by Instagram: {e}")
    except Exception as e:
        logger.error(f"[REPLY_COMMENT] Error replying to comment {comment_id} from {account.username}: {e}")
        raise
