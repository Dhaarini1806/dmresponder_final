# Testing Guide for Instagram Automation

## Prerequisites

- Django project running
- Celery worker running: `celery -A dmresponder worker -l info`
- Redis running on localhost:6379
- Instagram account connected in dmresponder
- Python shell access: `python manage.py shell`

---

## Test 1: Verify instagrapi Installation

```python
# In Django shell
from instagrapi import Client

cl = Client()
print(f"✅ instagrapi version: {cl.__version__}")
print(f"✅ Client initialized successfully")
```

**Expected Output:**
```
✅ instagrapi version: 2.1.3 (or higher)
✅ Client initialized successfully
```

---

## Test 2: Verify Session Manager

```python
from instagram.models import InstagramAccount
from instagram.session_manager import SessionManager

# Get your connected account
account = InstagramAccount.objects.filter(status='connected').first()

if not account:
    print("❌ No connected Instagram account found")
    print("   Please connect an account in the UI first")
else:
    print(f"✅ Found account: {account.username}")
    
    # Try to load session
    sm = SessionManager(account)
    if sm.cl.is_logged_in:
        print(f"✅ Session is active for {account.username}")
        print(f"✅ User ID: {sm.cl.user_id}")
    else:
        print(f"❌ Session not active for {account.username}")
        print(f"   Status: {account.status}")
```

**Expected Output:**
```
✅ Found account: my_instagram_handle
✅ Session is active for my_instagram_handle
✅ User ID: 123456789
```

---

## Test 3: Verify Action Executor

```python
from instagram.action_executor import ActionExecutor
from instagram.models import InstagramAccount

account = InstagramAccount.objects.filter(status='connected').first()

if not account:
    print("❌ No connected account")
else:
    executor = ActionExecutor()
    
    # Create a test action
    action = executor.submit(
        action_type='SEND_DM',
        payload={
            'account_id': account.pk,
            'recipient_id': '12345',  # Replace with real user ID
            'text': 'Test message from automation'
        },
        workflow_execution_id=None
    )
    
    print(f"✅ Action created: {action.execution_id}")
    print(f"✅ Status: {action.status}")
    print(f"✅ Action type: {action.action_type}")
    print(f"✅ Queued for processing")
```

**Expected Output:**
```
✅ Action created: 550e8400-e29b-41d4-a716-446655440000
✅ Status: PENDING
✅ Action type: SEND_DM
✅ Queued for processing
```

---

## Test 4: Wait for Celery Processing

```python
import time
from instagram.action_models import ActionExecution

# Use the execution_id from Test 3
execution_id = '550e8400-e29b-41d4-a716-446655440000'

print("⏳ Waiting for Celery to process...")
for i in range(10):
    action = ActionExecution.objects.get(execution_id=execution_id)
    print(f"  [{i+1}/10] Status: {action.status}")
    
    if action.status == 'SUCCESS':
        print(f"✅ Action succeeded!")
        print(f"✅ Response: {action.response_payload}")
        break
    elif action.status == 'DEAD_LETTER':
        print(f"❌ Action failed permanently")
        print(f"❌ Error: {action.error_message}")
        break
    
    time.sleep(1)
else:
    print("⏱️  Timeout - action still processing")
    print(f"   Check Celery logs for details")
```

**Expected Output (Success):**
```
⏳ Waiting for Celery to process...
  [1/10] Status: PENDING
  [2/10] Status: RUNNING
  [3/10] Status: SUCCESS
✅ Action succeeded!
✅ Response: {'status': 'sent', 'platform': 'instagram', 'recipient_id': '12345', 'message': 'Test message from automation', 'thread_id': 'thread_uuid'}
```

**Expected Output (Rate Limited):**
```
⏳ Waiting for Celery to process...
  [1/10] Status: PENDING
  [2/10] Status: RUNNING
  [3/10] Status: FAILED
  [4/10] Status: RUNNING
  [5/10] Status: SUCCESS
✅ Action succeeded! (after retry)
```

---

## Test 5: Full Workflow Test

```python
from automation.models import Workflow, WorkflowNode
from automation.services import WorkflowService
from instagram.models import InstagramAccount

# Get account
account = InstagramAccount.objects.filter(status='connected').first()

# Create a simple workflow
workflow = Workflow.objects.create(
    user=account.user,
    name="Test DM Workflow",
    description="Test sending DM via automation"
)

# Add send_dm node
node = WorkflowNode.objects.create(
    workflow=workflow,
    node_type='send_dm',
    config={
        'message': 'Hello from workflow automation!'
    },
    order=1
)

# Trigger workflow
context = {
    'trigger_data': {
        'account_pk': account.pk,
        'sender_id': '12345',  # Instagram user ID
        'username': 'test_user',
        'platform': 'instagram'
    },
    'execution_id': 'workflow-test-123'
}

result = WorkflowService.execute_workflow(workflow, context)
print(f"✅ Workflow executed: {result}")

# Check action was created
from instagram.action_models import ActionExecution
action = ActionExecution.objects.filter(
    workflow_execution_id='workflow-test-123'
).first()

if action:
    print(f"✅ Action created from workflow")
    print(f"✅ Action ID: {action.execution_id}")
    print(f"✅ Status: {action.status}")
else:
    print(f"❌ No action created from workflow")
```

**Expected Output:**
```
✅ Workflow executed: {'status': 'queued', 'platform': 'instagram', 'message': 'Hello from workflow automation!'}
✅ Action created from workflow
✅ Action ID: 550e8400-e29b-41d4-a716-446655440000
✅ Status: PENDING
```

---

## Test 6: Error Handling - Invalid User

```python
from instagram.action_executor import ActionExecutor
from instagram.models import InstagramAccount

account = InstagramAccount.objects.filter(status='connected').first()

# Try to send to non-existent user
action = executor.submit(
    action_type='SEND_DM',
    payload={
        'account_id': account.pk,
        'recipient_id': '999999999999',  # Non-existent user
        'text': 'This should fail'
    },
    workflow_execution_id=None
)

print(f"⏳ Processing action with invalid user...")
import time
time.sleep(5)

action.refresh_from_db()
print(f"Status: {action.status}")
print(f"Error: {action.error_message}")

if action.status == 'DEAD_LETTER':
    print(f"✅ Correctly handled invalid user error")
else:
    print(f"❌ Expected DEAD_LETTER status")
```

**Expected Output:**
```
⏳ Processing action with invalid user...
Status: DEAD_LETTER
Error: Instagram user 999999999999 not found
✅ Correctly handled invalid user error
```

---

## Test 7: Error Handling - Session Expired

```python
from instagram.models import InstagramAccount, InstagramSession

account = InstagramAccount.objects.filter(status='connected').first()

# Simulate session expiration by deleting session
try:
    session = InstagramSession.objects.get(account=account)
    session.delete()
    print("✅ Deleted session to simulate expiration")
except:
    print("❌ No session found to delete")

# Try to send DM with expired session
from instagram.action_executor import ActionExecutor
executor = ActionExecutor()

action = executor.submit(
    action_type='SEND_DM',
    payload={
        'account_id': account.pk,
        'recipient_id': '12345',
        'text': 'Test with expired session'
    },
    workflow_execution_id=None
)

print(f"⏳ Processing action with expired session...")
import time
time.sleep(5)

action.refresh_from_db()
print(f"Status: {action.status}")

if action.status == 'FAILED':
    print(f"✅ Action failed as expected (will retry)")
    print(f"Error: {action.error_message}")
elif action.status == 'DEAD_LETTER':
    print(f"⚠️  Action moved to dead letter (max retries exceeded)")
else:
    print(f"Status: {action.status}")
```

**Expected Output:**
```
✅ Deleted session to simulate expiration
⏳ Processing action with expired session...
Status: FAILED
✅ Action failed as expected (will retry)
Error: Session expired for my_account
```

---

## Test 8: Verify Celery Logs

```bash
# In a separate terminal, watch Celery logs:
celery -A dmresponder worker -l info

# You should see logs like:
# [tasks] Received task: instagram.action_tasks.execute_action_task[...]
# [SEND_DM] Successfully sent DM from my_account to user 12345: Test message...
# Task instagram.action_tasks.execute_action_task[...] succeeded
```

---

## Test 9: Query Action History

```python
from instagram.action_models import ActionExecution
from django.utils import timezone
from datetime import timedelta

# Get all actions from last hour
recent = ActionExecution.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=1)
).order_by('-created_at')

print(f"Recent actions: {recent.count()}")
print()

for action in recent[:10]:
    print(f"ID: {action.execution_id}")
    print(f"Type: {action.action_type}")
    print(f"Status: {action.status}")
    print(f"Account: {action.instagram_account.username}")
    print(f"Created: {action.created_at}")
    if action.error_message:
        print(f"Error: {action.error_message}")
    if action.response_payload:
        print(f"Response: {action.response_payload}")
    print("---")
```

---

## Test 10: Load Testing

```python
from instagram.action_executor import ActionExecutor
from instagram.models import InstagramAccount

account = InstagramAccount.objects.filter(status='connected').first()
executor = ActionExecutor()

# Submit 5 actions rapidly
print("Submitting 5 actions...")
actions = []
for i in range(5):
    action = executor.submit(
        action_type='SEND_DM',
        payload={
            'account_id': account.pk,
            'recipient_id': f'user_{i}',
            'text': f'Message {i}'
        },
        workflow_execution_id=None
    )
    actions.append(action)
    print(f"  [{i+1}/5] Queued: {action.execution_id}")

print()
print("⏳ Waiting for all to complete...")
import time
time.sleep(10)

# Check results
successful = 0
failed = 0
for action in actions:
    action.refresh_from_db()
    if action.status == 'SUCCESS':
        successful += 1
    elif action.status in ['FAILED', 'DEAD_LETTER']:
        failed += 1

print(f"✅ Successful: {successful}/5")
print(f"❌ Failed: {failed}/5")
```

---

## Troubleshooting Tests

### Celery Not Processing Tasks

```python
# Check if Celery worker is running
import celery
from dmresponder.celery import app

# Try to send a test task
result = app.control.inspect().active()
if result:
    print(f"✅ Celery workers active: {result}")
else:
    print(f"❌ No active Celery workers")
    print(f"   Run: celery -A dmresponder worker -l info")
```

### Redis Connection Issues

```python
# Check Redis connection
import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print(f"✅ Redis connected")
except Exception as e:
    print(f"❌ Redis error: {e}")
    print(f"   Make sure Redis is running: redis-server")
```

### Action Stuck in RUNNING

```python
from instagram.action_models import ActionExecution
from django.utils import timezone
from datetime import timedelta

# Find stuck actions
stuck = ActionExecution.objects.filter(
    status='RUNNING',
    started_at__lt=timezone.now() - timedelta(minutes=5)
)

if stuck.exists():
    print(f"⚠️  Found {stuck.count()} stuck actions:")
    for action in stuck:
        print(f"  - {action.execution_id} (started {action.started_at})")
    
    # Reset them
    stuck.update(status='FAILED', error_message='Timeout - worker crash')
    print(f"✅ Reset stuck actions to FAILED")
else:
    print(f"✅ No stuck actions found")
```

---

## Success Checklist

- [ ] Test 1: instagrapi imports successfully
- [ ] Test 2: Session manager loads active session
- [ ] Test 3: ActionExecutor creates PENDING action
- [ ] Test 4: Celery processes action to SUCCESS
- [ ] Test 5: Workflow triggers action creation
- [ ] Test 6: Invalid user error handled correctly
- [ ] Test 7: Session expiration error handled correctly
- [ ] Test 8: Celery logs show action execution
- [ ] Test 9: Action history queries work
- [ ] Test 10: Multiple actions process correctly

---

**All tests passing? ✅ Your Instagram automation is ready for production!**
