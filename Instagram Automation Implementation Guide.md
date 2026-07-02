# Instagram Automation Implementation Guide

## Overview

This document describes the **real Instagram automation implementation** that has been integrated into your dmresponder_final project. The system uses **instagrapi** to send direct messages, reply to messages, and reply to comments on Instagram.

## What Was Changed

### 1. **Fixed Account ID Bug** (`automation/services.py`)
**Issue:** The automation workflow was passing `account.account_id` (external string) to `ActionExecutor`, which expects the database primary key.

**Fix:** Changed line 91 to use `account.pk` instead:
```python
# Before:
payload = {'account_id': account.account_id, 'recipient_id': sender_id, 'text': message}

# After:
payload = {'account_id': account.pk, 'recipient_id': sender_id, 'text': message}
```

### 2. **Implemented Real Instagram Handlers** (`instagram/action_tasks.py`)
Replaced placeholder functions with actual instagrapi calls:

#### `_handle_send_dm(action_exec)`
- **Purpose:** Send a direct message to an Instagram user
- **Payload:** `{'account_id': int, 'recipient_id': str, 'text': str}`
- **Implementation:**
  - Gets authenticated instagrapi client via `InstagramService.get_instagram_client()`
  - Calls `client.direct_send(text, user_ids=[recipient_id])`
  - Handles errors: `UserNotFound`, `BadPassword`, `LoginRequired`, `PleaseWaitFewMinutes`
  - Returns success response with thread ID

#### `_handle_reply_dm(action_exec)`
- **Purpose:** Reply to a direct message thread
- **Payload:** `{'account_id': int, 'thread_id': str, 'text': str}`
- **Implementation:**
  - Gets authenticated instagrapi client
  - Calls `client.direct_send(text, thread_ids=[thread_id])`
  - Handles rate limits and session errors
  - Returns success response

#### `_handle_reply_comment(action_exec)`
- **Purpose:** Reply to a comment on a media post
- **Payload:** `{'account_id': int, 'comment_id': str, 'text': str}`
- **Implementation:**
  - Gets authenticated instagrapi client
  - Calls `client.comment_reply(text, comment_id)`
  - Handles `MediaNotFound`, `BadPassword`, rate limits
  - Returns success response with reply ID

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                        │
│  (automation/services.py - _execute_node)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Action Executor                                 │
│  (instagram/action_executor.py - ActionExecutor.submit)     │
│  - Validates payload                                         │
│  - Creates ActionExecution record                            │
│  - Enqueues task                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Celery Task Queue                               │
│  (instagram/queue_manager.py - enqueue_action)              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Action Task Worker                              │
│  (instagram/action_tasks.py - execute_action_task)          │
│  - Retrieves ActionExecution                                │
│  - Dispatches to handler                                    │
│  - Handles retries (3 attempts max)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   SEND_DM      REPLY_DM   REPLY_COMMENT
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Instagrapi Client                               │
│  (instagram/session_manager.py - SessionManager)            │
│  - Maintains authenticated session                          │
│  - Handles 2FA, challenges                                  │
│  - Persists session to database                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
              Instagram API
```

## Data Flow Example: Send DM

### 1. Workflow Triggers
```python
# From automation/services.py
context = {
    'trigger_data': {
        'account_pk': 1,
        'sender_id': '12345',  # Instagram user ID
    },
    'execution_id': 'workflow-exec-uuid'
}
message = "Hello from automation!"
```

### 2. Action Executor Creates Task
```python
# ActionExecutor.submit() creates ActionExecution record:
ActionExecution(
    execution_key='sha256_hash',
    workflow_execution_id='workflow-exec-uuid',
    action_type='SEND_DM',
    instagram_account=account,  # pk=1
    recipient='12345',
    status='PENDING',
    request_payload={
        'account_id': 1,
        'recipient_id': '12345',
        'text': 'Hello from automation!'
    }
)
```

### 3. Celery Task Executes
```python
# Celery worker picks up task:
execute_action_task(action_execution_id='uuid')
  ├─ Fetches ActionExecution record
  ├─ Sets status to RUNNING
  ├─ Calls _dispatch_action()
  │  └─ Routes to _handle_send_dm()
  │     ├─ Gets instagrapi client
  │     ├─ Calls client.direct_send(text, user_ids=[12345])
  │     └─ Returns success response
  ├─ Sets status to SUCCESS
  └─ Saves response_payload
```

### 4. Response Saved
```python
ActionExecution.response_payload = {
    'status': 'sent',
    'platform': 'instagram',
    'recipient_id': '12345',
    'message': 'Hello from automation!',
    'thread_id': 'thread_uuid'
}
```

## Error Handling & Retry Logic

### Retry Behavior
- **Max Attempts:** 3
- **Backoff:** Exponential (60s, 120s, 240s)
- **Status Progression:** `PENDING` → `RUNNING` → `SUCCESS` | `FAILED` | `DEAD_LETTER`

### Handled Exceptions

| Exception | Behavior | Action |
|-----------|----------|--------|
| `UserNotFound` | Permanent error | Move to DEAD_LETTER |
| `BadPassword` / `LoginRequired` | Session expired | Retry (may need re-login) |
| `PleaseWaitFewMinutes` | Rate limited | Retry with backoff |
| `MediaNotFound` | Comment not found | Move to DEAD_LETTER |
| Other exceptions | Unknown error | Retry up to 3 times |

### Monitoring Failed Actions
```python
# Check failed actions:
from instagram.action_models import ActionExecution

failed = ActionExecution.objects.filter(status='DEAD_LETTER')
for action in failed:
    print(f"{action.action_type}: {action.error_message}")
```

## Session Management

### How Sessions Work
1. **Login:** User provides Instagram credentials
   ```python
   from instagram.services import InstagramService
   account = InstagramAccount.objects.get(pk=1)
   InstagramService.login_instagram_account(account, username, password)
   ```

2. **Session Stored:** instagrapi session persisted to database
   ```python
   # In InstagramSession model
   session_json = client.get_settings()  # Contains cookies, headers, etc.
   ```

3. **Reuse:** Session loaded on next action
   ```python
   session_manager = SessionManager(account)
   session_manager._load_session()  # Restores from database
   client = session_manager.ensure_session_active()
   ```

4. **Refresh:** If session expires, automatic re-login attempted
   ```python
   # In session_manager.refresh_session():
   if not self.cl.is_logged_in:
       username = os.environ.get(f'INSTAGRAM_USERNAME_{account.pk}')
       password = os.environ.get(f'INSTAGRAM_PASSWORD_{account.pk}')
       self.login(username, password)
   ```

### Security Notes
- ⚠️ **Credentials in Environment:** Currently expects credentials in env vars for re-login
- ✅ **Session Persistence:** Sessions stored in database (encrypted recommended in production)
- ✅ **Challenge Handling:** 2FA and CAPTCHA challenges are caught and reported

## Testing the Implementation

### 1. Manual Test: Send DM
```python
from instagram.action_executor import ActionExecutor
from instagram.models import InstagramAccount

account = InstagramAccount.objects.get(pk=1)
executor = ActionExecutor()

# Submit action
action_exec = executor.submit(
    action_type='SEND_DM',
    payload={
        'account_id': account.pk,
        'recipient_id': '12345',  # Instagram user ID
        'text': 'Test message from automation'
    },
    workflow_execution_id=None
)

print(f"Action queued: {action_exec.execution_id}")
print(f"Status: {action_exec.status}")

# Check result after Celery processes it (wait a few seconds)
action_exec.refresh_from_db()
print(f"Result: {action_exec.response_payload}")
```

### 2. Manual Test: Reply to Comment
```python
executor = ActionExecutor()
action_exec = executor.submit(
    action_type='REPLY_COMMENT',
    payload={
        'account_id': account.pk,
        'comment_id': 'comment_pk_123',
        'text': 'Thanks for your comment!'
    },
    workflow_execution_id=None
)
```

### 3. Check Celery Logs
```bash
# In your project directory:
celery -A dmresponder worker -l info

# Look for logs like:
# [SEND_DM] Successfully sent DM from my_account to user 12345: Test message...
```

## Common Issues & Solutions

### Issue: "Session expired for account"
**Cause:** Instagram session cookie expired or was invalidated
**Solution:**
1. Re-login the account via the UI
2. Or set environment variables for auto-refresh:
   ```bash
   export INSTAGRAM_USERNAME_1="your_username"
   export INSTAGRAM_PASSWORD_1="your_password"
   ```

### Issue: "Rate limited by Instagram"
**Cause:** Too many requests in short time
**Solution:**
- The system automatically retries with exponential backoff
- Increase delays in `instagram/utils.py` (REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
- Reduce polling frequency for comments and DMs

### Issue: "User not found" error
**Cause:** Recipient Instagram user ID is invalid or account is deleted
**Solution:**
- Verify the user ID is correct (should be numeric Instagram ID, not username)
- Check if the user account still exists
- Use `client.user_id_from_username(username)` to get correct ID

### Issue: Action stuck in RUNNING status
**Cause:** Celery worker crashed or task was interrupted
**Solution:**
```python
from instagram.action_models import ActionExecution
from django.utils import timezone

# Reset stuck actions to FAILED
stuck = ActionExecution.objects.filter(
    status='RUNNING',
    started_at__lt=timezone.now() - timedelta(hours=1)
)
stuck.update(status='FAILED', error_message='Timeout - worker crash')
```

## Configuration & Tuning

### Polling Intervals
Edit `instagram/utils.py`:
```python
# Delay between API requests (avoid rate limiting)
REQUEST_DELAY_MIN = 1.0  # seconds
REQUEST_DELAY_MAX = 3.0  # seconds

# Max items to fetch per poll
MAX_CONVERSATIONS = 20
MAX_MESSAGES_PER_CONVERSATION = 10
MAX_MEDIA_FETCH = 10
MAX_COMMENT_FETCH = 20
```

### Retry Strategy
Edit `instagram/action_tasks.py`:
```python
MAX_ATTEMPTS = 3  # Change to 5 for more resilience

# Backoff formula: 60 * (2 ** attempt_number)
# Attempt 1: 60s
# Attempt 2: 120s
# Attempt 3: 240s
```

### Celery Configuration
Edit `dmresponder/settings.py`:
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
```

## Deployment Checklist

- [ ] Verify `instagrapi>=2.1.3` is in `requirements.txt`
- [ ] Run `pip install -r requirements.txt` in production
- [ ] Set up Redis for Celery broker
- [ ] Start Celery worker: `celery -A dmresponder worker -l info`
- [ ] Start Celery beat for scheduled tasks: `celery -A dmresponder beat -l info`
- [ ] Configure Instagram account credentials securely
- [ ] Test SEND_DM action with a test account
- [ ] Monitor `ActionExecution` table for errors
- [ ] Set up alerts for DEAD_LETTER actions
- [ ] Document Instagram API rate limits for your use case

## Next Steps

1. **Test in Development:** Use a demo Instagram account to test automation
2. **Monitor Logs:** Watch for errors in Celery worker logs
3. **Adjust Delays:** Tune REQUEST_DELAY_MIN/MAX based on rate limiting
4. **Scale Gradually:** Start with a few accounts, monitor performance
5. **Add Monitoring:** Set up alerts for failed actions
6. **Document Workflows:** Create runbooks for common automation scenarios

## Support & Debugging

### Enable Debug Logging
```python
# In dmresponder/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'instagram': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Inspect Action Execution Records
```python
from instagram.action_models import ActionExecution
from django.db.models import Q

# Get all actions for an account
account_id = 1
actions = ActionExecution.objects.filter(instagram_account_id=account_id)

# Get failed actions
failed = actions.filter(status='DEAD_LETTER')

# Get recent actions
from django.utils import timezone
from datetime import timedelta
recent = actions.filter(created_at__gte=timezone.now() - timedelta(hours=1))

# Print details
for action in failed:
    print(f"Type: {action.action_type}")
    print(f"Status: {action.status}")
    print(f"Error: {action.error_message}")
    print(f"Payload: {action.request_payload}")
    print(f"Response: {action.response_payload}")
    print("---")
```

## References

- **instagrapi Documentation:** https://subzeroid.github.io/instagrapi/
- **Django Celery:** https://docs.celeryproject.org/en/stable/django/
- **Instagram API Limits:** https://help.instagram.com/1986234648360433

---

**Last Updated:** July 2, 2026  
**Implementation Status:** ✅ Complete - Real instagrapi integration active
