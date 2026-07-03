import logging
from celery import shared_task
from django.db.models import Q
from instagrapi.exceptions import LoginRequired
from .models import InstagramAccount
from .comment_listener import CommentListener
from .exceptions import InstagramRateLimitException, InstagramException
from .utils import RETRY_LIMIT, BACKOFF_MULTIPLIER

logger = logging.getLogger(__name__)

@shared_task
def poll_all_accounts_comments():
    """
    Periodic task that finds all active Instagram accounts (connected or demo)
    and queues a polling task for each.
    """
    logger.info("Starting periodic task: poll_all_accounts_comments")
    active_accounts = InstagramAccount.objects.filter(
        Q(status__in=['connected', 'demo']) | Q(is_demo=True),
        automation_status=True
    )
    
    count = 0
    for account in active_accounts:
        poll_single_account_comments.delay(account.id)
        count += 1
        
    logger.info(f"Queued comment polling tasks for {count} Instagram accounts.")
    return f"Queued {count} tasks"

@shared_task(bind=True, max_retries=RETRY_LIMIT)
def poll_single_account_comments(self, account_id):
    """
    Task that polls comments for a single Instagram account.
    Retries on transient rate-limiting or connection errors.
    """
    try:
        account = InstagramAccount.objects.get(pk=account_id)
    except InstagramAccount.DoesNotExist:
        logger.error(f"InstagramAccount with ID {account_id} does not exist.")
        return f"Account {account_id} not found"

    logger.info(f"Executing comment poll for account: {account.username}")
    try:
        listener = CommentListener(account)
        new_comments = listener.poll_account()
        return f"Successfully polled {account.username}. Found {new_comments} new comments."
    except LoginRequired as exc:
        logger.warning(f"Session expired (LoginRequired) for {account.username}. Marking status as disconnected.")
        account.status = 'disconnected'
        account.save()
        return f"Session expired for {account.username}."
    except InstagramRateLimitException as exc:
        # Rate limits are common, retry with exponential backoff
        countdown = (BACKOFF_MULTIPLIER ** self.request.retries) * 60
        logger.warning(f"Rate limited for {account.username}. Retrying in {countdown}s. Error: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
    except InstagramException as exc:
        # Generic integration error, retry with longer backoff
        countdown = (BACKOFF_MULTIPLIER ** self.request.retries) * 120
        logger.warning(f"Instagram error for {account.username}. Retrying in {countdown}s. Error: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        # Check if the error itself implies login is required
        if isinstance(exc, Exception) and "login_required" in str(exc).lower():
            logger.warning(f"Session expired (login required exception) for {account.username}. Marking status as disconnected.")
            account.status = 'disconnected'
            account.save()
            return f"Session expired for {account.username}."
        # Unexpected error, log and fail (do not retry continuously)
        logger.error(f"Unexpected error polling comments for {account.username}: {exc}", exc_info=True)
        return f"Failed: {str(exc)}"


@shared_task
def poll_all_accounts_dms():
    """
    Periodic task that finds all active Instagram accounts (connected or demo)
    and queues a DM polling task for each.
    """
    logger.info("Starting periodic task: poll_all_accounts_dms")
    active_accounts = InstagramAccount.objects.filter(
        Q(status__in=['connected', 'demo']) | Q(is_demo=True),
        automation_status=True
    )
    
    count = 0
    for account in active_accounts:
        poll_single_account_dms.delay(account.id)
        count += 1
        
    logger.info(f"Queued DM polling tasks for {count} Instagram accounts.")
    return f"Queued {count} tasks"


@shared_task(bind=True, max_retries=RETRY_LIMIT)
def poll_single_account_dms(self, account_id):
    """
    Task that polls direct messages for a single Instagram account.
    Retries on transient rate-limiting or connection errors.
    """
    from .dm_listener import DMListener
    
    try:
        account = InstagramAccount.objects.get(pk=account_id)
    except InstagramAccount.DoesNotExist:
        logger.error(f"InstagramAccount with ID {account_id} does not exist.")
        return f"Account {account_id} not found"

    logger.info(f"Executing DM poll for account: {account.username}")
    try:
        listener = DMListener(account)
        new_messages = listener.poll_inbox()
        return f"Successfully polled DMs for {account.username}. Found {new_messages} new messages."
    except LoginRequired as exc:
        logger.warning(f"Session expired (LoginRequired) for {account.username}. Marking status as disconnected.")
        account.status = 'disconnected'
        account.save()
        return f"Session expired for {account.username}."
    except InstagramRateLimitException as exc:
        countdown = (BACKOFF_MULTIPLIER ** self.request.retries) * 60
        logger.warning(f"Rate limited for {account.username} DMs. Retrying in {countdown}s. Error: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
    except InstagramException as exc:
        countdown = (BACKOFF_MULTIPLIER ** self.request.retries) * 120
        logger.warning(f"Instagram DM error for {account.username}. Retrying in {countdown}s. Error: {exc}")
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        if isinstance(exc, Exception) and "login_required" in str(exc).lower():
            logger.warning(f"Session expired (login required exception) for {account.username}. Marking status as disconnected.")
            account.status = 'disconnected'
            account.save()
            return f"Session expired for {account.username}."
        logger.error(f"Unexpected error polling DMs for {account.username}: {exc}", exc_info=True)
        return f"Failed: {str(exc)}"

