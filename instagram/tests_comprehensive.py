"""
Comprehensive test suite for DMResponder Instagram automation platform.

Run with:
    python manage.py test instagram.tests_comprehensive --verbosity=2
"""

from django.test import TestCase, Client as DjangoClient
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from unittest.mock import MagicMock, patch, call
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from instagram.models import (
    InstagramAccount, InstagramReel, CommentLog, DMLog,
    InstagramSession, InstagramComment
)
from instagram.exceptions import (
    InstagramException, InstagramRateLimitException, InstagramChallengeException
)
from instagram.comment_listener import CommentListener
from instagram.dm_listener import DMListener
from instagram.workflow_bridge import WorkflowBridge
from automation.models import AutomationWorkflow, AutomationExecution, WorkflowNode
from inbox.models import Conversation, Message
from crm.models import Lead, LeadTimeline


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_user(username="testuser", password="testpass123"):
    return User.objects.create_user(username=username, password=password)


def make_account(user, username="test_insta", account_id="IG001", status="connected", is_demo=False):
    return InstagramAccount.objects.create(
        user=user,
        username=username,
        account_id=account_id,
        status=status,
        is_demo=is_demo,
        automation_status=True,
    )


def jwt_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ─────────────────────────────────────────────────────────────────────────────
# 1. Exceptions — import sanity
# ─────────────────────────────────────────────────────────────────────────────

class ExceptionDefinitionsTest(TestCase):
    """Verify all custom exceptions are importable and form a correct hierarchy."""

    def test_instagram_exception_is_base_exception(self):
        exc = InstagramException("test")
        self.assertIsInstance(exc, Exception)

    def test_rate_limit_is_subclass(self):
        exc = InstagramRateLimitException("rate limited")
        self.assertIsInstance(exc, InstagramException)

    def test_challenge_is_subclass(self):
        exc = InstagramChallengeException("challenge", challenge_url="https://ig.com/challenge")
        self.assertIsInstance(exc, InstagramException)
        self.assertEqual(exc.challenge_url, "https://ig.com/challenge")

    def test_challenge_default_url(self):
        exc = InstagramChallengeException("no url")
        self.assertEqual(exc.challenge_url, "")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Session Manager
# ─────────────────────────────────────────────────────────────────────────────

class SessionManagerTest(TestCase):
    """Unit tests for SessionManager: login, save, load, logout flows."""

    def setUp(self):
        self.user = make_user("sm_user")
        self.account = make_account(self.user, account_id="SM001")

    @patch("instagram.session_manager.Client")
    def test_load_session_from_db_on_init(self, MockClient):
        """__init__ should call set_settings if a session record exists."""
        session_data = {"device_id": "abc123"}
        InstagramSession.objects.create(account=self.account, session_json=session_data)

        mock_cl = MockClient.return_value
        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        mock_cl.set_settings.assert_called_once_with(session_data)

    @patch("instagram.session_manager.Client")
    def test_no_session_init_ok(self, MockClient):
        """__init__ succeeds even when no session record exists."""
        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)  # Should not raise

    @patch("instagram.session_manager.Client")
    def test_login_success_saves_session_and_updates_status(self, MockClient):
        mock_cl = MockClient.return_value
        mock_cl.is_logged_in = False

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl
        mock_cl.get_settings.return_value = {"session": "data"}

        result = sm.login("user", "pass")
        self.assertTrue(result)
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "connected")

    @patch("instagram.session_manager.Client")
    def test_login_bad_password_raises_instagram_exception(self, MockClient):
        from instagrapi.exceptions import BadPassword
        mock_cl = MockClient.return_value
        mock_cl.is_logged_in = False
        mock_cl.login.side_effect = BadPassword("wrong password")
        mock_cl.get_settings.return_value = {}

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl

        with self.assertRaises(InstagramException):
            sm.login("user", "wrongpass")

        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "disconnected")

    @patch("instagram.session_manager.Client")
    def test_login_challenge_raises_instagram_challenge_exception(self, MockClient):
        from instagrapi.exceptions import ChallengeRequired
        mock_cl = MockClient.return_value
        mock_cl.is_logged_in = False
        exc = ChallengeRequired()
        exc.challenge_url = "https://ig.com/challenge"
        mock_cl.login.side_effect = exc
        mock_cl.get_settings.return_value = {}

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl

        with self.assertRaises(InstagramChallengeException):
            sm.login("user", "pass")

        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "pending")

    @patch("instagram.session_manager.Client")
    def test_login_rate_limit_raises_instagram_rate_limit_exception(self, MockClient):
        from instagrapi.exceptions import PleaseWaitFewMinutes
        mock_cl = MockClient.return_value
        mock_cl.is_logged_in = False
        mock_cl.login.side_effect = PleaseWaitFewMinutes("wait")
        mock_cl.get_settings.return_value = {}

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl

        with self.assertRaises(InstagramRateLimitException):
            sm.login("user", "pass")

    @patch("instagram.session_manager.Client")
    def test_already_logged_in_skips_login_call(self, MockClient):
        mock_cl = MockClient.return_value
        mock_cl.is_logged_in = True
        mock_cl.get_settings.return_value = {}

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl

        result = sm.login("user", "pass")
        self.assertTrue(result)
        mock_cl.login.assert_not_called()

    @patch("instagram.session_manager.Client")
    def test_logout_deletes_session_record(self, MockClient):
        mock_cl = MockClient.return_value
        InstagramSession.objects.create(account=self.account, session_json={})

        from instagram.session_manager import SessionManager
        sm = SessionManager(self.account)
        sm.cl = mock_cl
        sm.logout()

        self.assertFalse(InstagramSession.objects.filter(account=self.account).exists())
        self.account.refresh_from_db()
        self.assertEqual(self.account.status, "disconnected")

    @patch("instagram.session_manager.Client")
    def test_session_persistence_save_and_reload(self, MockClient):
        """_save_session stores JSON; a second __init__ can reload it."""
        from instagram.session_manager import SessionManager
        mock_cl = MockClient.return_value
        mock_cl.get_settings.return_value = {"cookie": "abc"}

        sm = SessionManager(self.account)
        sm.cl = mock_cl
        sm._save_session()

        session = InstagramSession.objects.get(account=self.account)
        self.assertEqual(session.session_json, {"cookie": "abc"})


# ─────────────────────────────────────────────────────────────────────────────
# 3. Comment Listener
# ─────────────────────────────────────────────────────────────────────────────

class CommentListenerTest(TestCase):

    def setUp(self):
        self.user = make_user("cl_user")
        self.account = make_account(self.user, account_id="CL001")
        self.workflow = AutomationWorkflow.objects.create(
            user=self.user,
            name="Comment Workflow",
            status="active",
            trigger_type="comment",
            trigger_config={"keyword": "price"},
        )

    @patch("instagram.comment_listener.InstagramService.get_instagram_client")
    def test_poll_real_account_creates_comment(self, mock_get_client):
        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id_from_username.return_value = "uid_999"

        mock_media = MagicMock()
        mock_media.pk = "media_001"
        mock_cl.user_medias.return_value = [mock_media]

        mock_comment = MagicMock()
        mock_comment.pk = "cmt_001"
        mock_comment.text = "What is the price?"
        mock_comment.user.username = "buyer_01"
        mock_comment.created_at = timezone.now()
        mock_cl.media_comments.return_value = [mock_comment]

        listener = CommentListener(self.account)
        count = listener.poll_account()

        self.assertEqual(count, 1)
        comment = InstagramComment.objects.get(comment_id="cmt_001")
        self.assertEqual(comment.text, "What is the price?")
        self.assertTrue(comment.processed)

    @patch("instagram.comment_listener.InstagramService.get_instagram_client")
    def test_duplicate_comment_not_created_twice(self, mock_get_client):
        InstagramComment.objects.create(
            account=self.account,
            comment_id="cmt_dup",
            media_id="media_001",
            username="dup_user",
            text="Already in DB",
            timestamp=timezone.now(),
            processed=True,
        )

        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id_from_username.return_value = "uid_999"

        mock_media = MagicMock()
        mock_media.pk = "media_001"
        mock_cl.user_medias.return_value = [mock_media]

        mock_comment = MagicMock()
        mock_comment.pk = "cmt_dup"
        mock_comment.text = "Already in DB"
        mock_comment.user.username = "dup_user"
        mock_comment.created_at = timezone.now()
        mock_cl.media_comments.return_value = [mock_comment]

        listener = CommentListener(self.account)
        count = listener.poll_account()

        self.assertEqual(count, 0)
        self.assertEqual(InstagramComment.objects.filter(comment_id="cmt_dup").count(), 1)

    def test_demo_account_generates_comments(self):
        demo_account = make_account(self.user, username="demo_ig", account_id="DEMO001", is_demo=True)
        listener = CommentListener(demo_account)
        count = listener.poll_account()
        self.assertGreater(count, 0)
        saved = InstagramComment.objects.filter(account=demo_account)
        self.assertEqual(saved.count(), count)

    @patch("instagram.comment_listener.InstagramService.get_instagram_client")
    def test_poll_failure_propagates_exception(self, mock_get_client):
        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id_from_username.side_effect = Exception("Network error")

        listener = CommentListener(self.account)
        with self.assertRaises(Exception) as ctx:
            listener.poll_account()
        self.assertIn("Network error", str(ctx.exception))

    @patch("instagram.comment_listener.InstagramService.get_instagram_client")
    def test_demo_flag_skips_real_client(self, mock_get_client):
        demo_account = make_account(self.user, username="demo_2", account_id="DEMO002", is_demo=True)
        listener = CommentListener(demo_account)
        listener.poll_account()
        mock_get_client.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 4. DM Listener
# ─────────────────────────────────────────────────────────────────────────────

class DMListenerTest(TestCase):

    def setUp(self):
        self.user = make_user("dm_user")
        self.account = make_account(self.user, account_id="DM001")
        self.workflow = AutomationWorkflow.objects.create(
            user=self.user,
            name="DM Workflow",
            status="active",
            trigger_type="message",
            trigger_config={"keyword": "info"},
        )

    @patch("instagram.dm_listener.InstagramService.get_instagram_client")
    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_new_message_saved_and_workflow_triggered(self, mock_exec, mock_get_client):
        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id = "our_user_id"

        mock_user = MagicMock()
        mock_user.pk = "participant_01"
        mock_user.username = "alice"
        mock_user.full_name = "Alice Smith"

        mock_thread = MagicMock()
        mock_thread.id = "thread_001"
        mock_thread.users = [mock_user]
        mock_cl.direct_threads.return_value = [mock_thread]

        mock_msg = MagicMock()
        mock_msg.id = "msg_001"
        mock_msg.user_id = "participant_01"
        mock_msg.item_type = "text"
        mock_msg.text = "Can I get more info?"
        mock_msg.timestamp = timezone.now()
        mock_msg.dict.return_value = {"id": "msg_001", "text": "Can I get more info?"}
        mock_cl.direct_messages.return_value = [mock_msg]

        listener = DMListener(self.account)
        count = listener.poll_inbox()

        self.assertEqual(count, 1)
        conv = Conversation.objects.get(conversation_id="thread_001")
        self.assertEqual(conv.participant_username, "alice")

        msg = Message.objects.get(message_id="msg_001")
        self.assertEqual(msg.message_text, "Can I get more info?")
        self.assertEqual(msg.sender_type, "participant")
        self.assertTrue(msg.processed)
        mock_exec.assert_called_once()

    @patch("instagram.dm_listener.InstagramService.get_instagram_client")
    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_duplicate_message_not_saved_twice(self, mock_exec, mock_get_client):
        conv = Conversation.objects.create(
            user=self.user,
            instagram_account=self.account,
            conversation_id="thread_dup",
            participant_id="p_dup",
            participant_username="dup_sender",
            platform="instagram",
        )
        Message.objects.create(
            conversation=conv,
            sender_type="participant",
            sender_id="p_dup",
            sender_username="dup_sender",
            message_text="Already saved",
            message_id="msg_dup",
            timestamp=timezone.now(),
            processed=True,
        )

        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id = "our_user_id"

        mock_user = MagicMock()
        mock_user.pk = "p_dup"
        mock_user.username = "dup_sender"
        mock_user.full_name = "Dup Sender"

        mock_thread = MagicMock()
        mock_thread.id = "thread_dup"
        mock_thread.users = [mock_user]
        mock_cl.direct_threads.return_value = [mock_thread]

        mock_msg = MagicMock()
        mock_msg.id = "msg_dup"
        mock_msg.user_id = "p_dup"
        mock_msg.item_type = "text"
        mock_msg.text = "Already saved"
        mock_msg.timestamp = timezone.now()
        mock_cl.direct_messages.return_value = [mock_msg]

        listener = DMListener(self.account)
        count = listener.poll_inbox()

        self.assertEqual(count, 0)
        mock_exec.assert_not_called()

    def test_demo_account_generates_messages(self):
        demo_account = make_account(self.user, username="demo_dm", account_id="DMDEMO", is_demo=True)
        listener = DMListener(demo_account)
        count = listener.poll_inbox()
        self.assertGreater(count, 0)
        msgs = Message.objects.filter(conversation__instagram_account=demo_account)
        self.assertGreater(msgs.count(), 0)

    @patch("instagram.dm_listener.InstagramService.get_instagram_client")
    def test_demo_flag_skips_real_client(self, mock_get_client):
        demo_account = make_account(self.user, username="demo_dm2", account_id="DMDEMO2", is_demo=True)
        DMListener(demo_account).poll_inbox()
        mock_get_client.assert_not_called()

    @patch("instagram.dm_listener.InstagramService.get_instagram_client")
    def test_outbound_message_not_counted_as_new(self, mock_get_client):
        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id = "our_user_id"

        mock_user = MagicMock()
        mock_user.pk = "participant_02"
        mock_user.username = "follower_x"
        mock_user.full_name = "Follower X"

        mock_thread = MagicMock()
        mock_thread.id = "thread_002"
        mock_thread.users = [mock_user]
        mock_cl.direct_threads.return_value = [mock_thread]

        mock_msg = MagicMock()
        mock_msg.id = "msg_002"
        mock_msg.user_id = "our_user_id"  # outbound
        mock_msg.item_type = "text"
        mock_msg.text = "Hey, this is us replying!"
        mock_msg.timestamp = timezone.now()
        mock_msg.dict.return_value = {}
        mock_cl.direct_messages.return_value = [mock_msg]

        listener = DMListener(self.account)
        count = listener.poll_inbox()

        self.assertEqual(count, 0)

    @patch("instagram.dm_listener.InstagramService.get_instagram_client")
    def test_group_conversation_participants_stored(self, mock_get_client):
        mock_cl = MagicMock()
        mock_get_client.return_value = mock_cl
        mock_cl.user_id = "our_user_id"

        mock_user1 = MagicMock()
        mock_user1.pk = "user_grp_1"
        mock_user1.username = "alice_group"
        mock_user1.full_name = "Alice"

        mock_user2 = MagicMock()
        mock_user2.pk = "user_grp_2"
        mock_user2.username = "bob_group"
        mock_user2.full_name = "Bob"

        mock_thread = MagicMock()
        mock_thread.id = "thread_group_001"
        mock_thread.users = [mock_user1, mock_user2]
        mock_cl.direct_threads.return_value = [mock_thread]
        mock_cl.direct_messages.return_value = []

        listener = DMListener(self.account)
        listener.poll_inbox()

        conv = Conversation.objects.get(conversation_id="thread_group_001")
        self.assertIn("alice_group", conv.participant_username)
        self.assertIn("bob_group", conv.participant_username)
        self.assertEqual(len(conv.participants), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Workflow Bridge
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowBridgeTest(TestCase):

    def setUp(self):
        self.user = make_user("wb_user")
        self.account = make_account(self.user, account_id="WB001")

    def _make_comment(self, comment_id="wbc_001", text="hello"):
        return InstagramComment.objects.create(
            account=self.account,
            comment_id=comment_id,
            media_id="media_wb",
            username="commenter",
            text=text,
            timestamp=timezone.now(),
            processed=False,
        )

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_keyword_match_triggers_workflow(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="Price WF",
            status="active",
            trigger_type="comment",
            trigger_config={"keyword": "price"},
        )
        comment = self._make_comment(text="What is the price?")
        WorkflowBridge.trigger_comment_workflow(comment)
        mock_exec.assert_called_once()
        comment.refresh_from_db()
        self.assertTrue(comment.processed)

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_keyword_no_match_does_not_trigger(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="Price WF",
            status="active",
            trigger_type="comment",
            trigger_config={"keyword": "price"},
        )
        comment = self._make_comment(comment_id="wbc_002", text="Just saying hi!")
        WorkflowBridge.trigger_comment_workflow(comment)
        mock_exec.assert_not_called()
        comment.refresh_from_db()
        self.assertTrue(comment.processed)

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_empty_keyword_triggers_all_comments(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="Any Comment WF",
            status="active",
            trigger_type="comment",
            trigger_config={},
        )
        comment = self._make_comment(comment_id="wbc_003", text="Random comment")
        WorkflowBridge.trigger_comment_workflow(comment)
        mock_exec.assert_called_once()

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_inactive_workflow_not_triggered(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="Inactive WF",
            status="inactive",
            trigger_type="comment",
            trigger_config={"keyword": ""},
        )
        comment = self._make_comment(comment_id="wbc_004", text="Any text")
        WorkflowBridge.trigger_comment_workflow(comment)
        mock_exec.assert_not_called()

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_keyword_case_insensitive(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="Price WF2",
            status="active",
            trigger_type="comment",
            trigger_config={"keyword": "price"},
        )
        comment = self._make_comment(comment_id="wbc_005", text="PRICE PLEASE!")
        WorkflowBridge.trigger_comment_workflow(comment)
        mock_exec.assert_called_once()

    @patch("instagram.workflow_bridge.AutomationService.execute_workflow")
    def test_trigger_message_workflow(self, mock_exec):
        AutomationWorkflow.objects.create(
            user=self.user,
            name="DM WF",
            status="active",
            trigger_type="message",
            trigger_config={"keyword": "info"},
        )
        conv = Conversation.objects.create(
            user=self.user,
            instagram_account=self.account,
            conversation_id="thread_wb",
            participant_id="p_wb",
            participant_username="wb_sender",
            platform="instagram",
        )
        msg = Message.objects.create(
            conversation=conv,
            sender_type="participant",
            sender_id="p_wb",
            sender_username="wb_sender",
            message_text="I want info about the product",
            message_id="msg_wb_001",
            timestamp=timezone.now(),
            processed=False,
        )
        WorkflowBridge.trigger_message_workflow(msg)
        mock_exec.assert_called_once()
        msg.refresh_from_db()
        self.assertTrue(msg.processed)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Automation Service — Workflow Execution
# ─────────────────────────────────────────────────────────────────────────────

class AutomationServiceTest(TestCase):

    def setUp(self):
        self.user = make_user("as_user")
        self.account = make_account(self.user, account_id="AS001")
        self.workflow = AutomationWorkflow.objects.create(
            user=self.user,
            name="Test WF",
            status="active",
            trigger_type="comment",
            trigger_config={},
        )

    def test_execute_workflow_no_trigger_node_fails(self):
        from automation.services import AutomationService
        execution = AutomationService.execute_workflow(self.workflow, {"test": True})
        self.assertEqual(execution.status, "failed")
        self.assertIn("No trigger node", execution.execution_data.get("error", ""))

    def test_execute_workflow_creates_execution_record(self):
        from automation.services import AutomationService
        AutomationService.execute_workflow(self.workflow, {"test": True})
        self.assertEqual(AutomationExecution.objects.filter(workflow=self.workflow).count(), 1)

    def test_execute_workflow_with_save_lead_node(self):
        from automation.services import AutomationService
        trigger_node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_id="trigger_01",
            node_type="trigger",
            config={},
        )
        save_node = WorkflowNode.objects.create(
            workflow=self.workflow,
            node_id="save_01",
            node_type="save_lead",
            config={},
        )
        from automation.models import WorkflowConnection
        WorkflowConnection.objects.create(
            workflow=self.workflow,
            source_node=trigger_node,
            target_node=save_node,
        )
        trigger_data = {"username": "test_lead", "platform": "instagram"}
        execution = AutomationService.execute_workflow(self.workflow, trigger_data)
        self.assertEqual(execution.status, "success")
        lead = Lead.objects.filter(user=self.user, name="test_lead").first()
        self.assertIsNotNone(lead)

    def test_disabled_workflow_not_triggered_by_bridge(self):
        from automation.services import AutomationService
        inactive_wf = AutomationWorkflow.objects.create(
            user=self.user,
            name="Inactive",
            status="inactive",
            trigger_type="comment",
            trigger_config={"keyword": ""},
        )
        active_wfs = AutomationWorkflow.objects.filter(
            user=self.user, status="active", trigger_type="comment"
        )
        self.assertNotIn(inactive_wf, active_wfs)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Celery Tasks
# ─────────────────────────────────────────────────────────────────────────────

class CeleryTasksTest(TestCase):

    def setUp(self):
        self.user = make_user("ct_user")
        self.demo_account = make_account(
            self.user, username="celery_demo", account_id="CT001", is_demo=True
        )

    def test_poll_all_accounts_comments_queues_tasks(self):
        from instagram.tasks import poll_all_accounts_comments
        result = poll_all_accounts_comments()
        self.assertIn("Queued", result)

    def test_poll_single_account_comments_nonexistent_account(self):
        from instagram.tasks import poll_single_account_comments
        result = poll_single_account_comments(9999999)
        self.assertIn("not found", result)

    def test_poll_single_account_comments_demo(self):
        from instagram.tasks import poll_single_account_comments
        result = poll_single_account_comments(self.demo_account.id)
        self.assertIn("Successfully polled", result)

    def test_poll_all_accounts_dms_queues_tasks(self):
        from instagram.tasks import poll_all_accounts_dms
        result = poll_all_accounts_dms()
        self.assertIn("Queued", result)

    def test_poll_single_account_dms_demo(self):
        from instagram.tasks import poll_single_account_dms
        result = poll_single_account_dms(self.demo_account.id)
        self.assertIn("Successfully polled DMs", result)

    def test_poll_tasks_only_target_active_accounts(self):
        inactive = make_account(
            self.user, username="inactive_acct", account_id="CT002", is_demo=True
        )
        inactive.automation_status = False
        inactive.save()

        from instagram.tasks import poll_all_accounts_comments
        poll_all_accounts_comments()
        self.assertEqual(InstagramComment.objects.filter(account=inactive).count(), 0)

    @patch("instagram.tasks.CommentListener")
    def test_rate_limit_exception_triggers_retry(self, MockListener):
        from instagram.tasks import poll_single_account_comments
        from celery.exceptions import Retry

        mock_listener = MockListener.return_value
        mock_listener.poll_account.side_effect = InstagramRateLimitException("rate limited")

        with self.assertRaises((Retry, InstagramRateLimitException, Exception)):
            poll_single_account_comments(self.demo_account.id)


# ─────────────────────────────────────────────────────────────────────────────
# 8. API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

class APIAuthTest(TestCase):

    def setUp(self):
        self.user = make_user("api_user")
        self.authed = jwt_client(self.user)
        self.anon = APIClient()

    def _check_requires_auth(self, url):
        response = self.anon.get(url)
        self.assertIn(
            response.status_code, [401, 403],
            f"Expected 401/403 from {url}, got {response.status_code}"
        )

    def test_instagram_accounts_requires_auth(self):
        self._check_requires_auth("/api/instagram/accounts/")

    def test_automation_workflows_requires_auth(self):
        self._check_requires_auth("/api/automation/workflows/")

    def test_crm_leads_requires_auth(self):
        self._check_requires_auth("/api/crm/leads/")

    def test_inbox_conversations_requires_auth(self):
        self._check_requires_auth("/api/inbox/conversations/")

    def test_instagram_accounts_list(self):
        make_account(self.user, account_id="API001")
        response = self.authed.get("/api/instagram/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_accounts_isolated_per_user(self):
        user_b = make_user("api_user_b")
        make_account(user_b, account_id="BAPI001")

        response = self.authed.get("/api/instagram/accounts/")
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_create_lead_authenticated(self):
        response = self.authed.post("/api/crm/leads/", {
            "name": "Test Lead",
            "source": "instagram",
            "status": "new",
        }, format="json")
        self.assertEqual(response.status_code, 201)

    def test_crm_leads_isolated_per_user(self):
        user_b = make_user("api_user_c")
        Lead.objects.create(user=user_b, name="B's Lead", source="instagram", status="new")

        response = self.authed.get("/api/crm/leads/")
        data = response.json()
        self.assertEqual(data["count"], 0)

    def test_jwt_token_obtain(self):
        response = APIClient().post("/api/token/", {
            "username": "api_user",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_jwt_token_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        response = APIClient().post("/api/token/refresh/", {"refresh": str(refresh)})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_invalid_credentials_rejected(self):
        response = APIClient().post("/api/token/", {
            "username": "api_user",
            "password": "WRONGPASSWORD",
        })
        self.assertEqual(response.status_code, 401)

    def test_connect_demo_endpoint(self):
        """POST /api/instagram/accounts/create_demo_account/ should create a demo account."""
        response = self.authed.post("/api/instagram/accounts/create_demo_account/")
        self.assertEqual(response.status_code, 201, f"Expected 201, got {response.status_code}: {response.json()}")
        data = response.json()
        self.assertEqual(data.get("status"), "demo")
        self.assertTrue(data.get("is_demo"))

    def test_automation_workflow_create(self):
        response = self.authed.post("/api/automation/workflows/", {
            "name": "My Workflow",
            "trigger_type": "comment",
            "status": "active",
            "trigger_config": {},
        }, format="json")
        self.assertEqual(response.status_code, 201)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Dashboard Views (HTTP page responses)
# ─────────────────────────────────────────────────────────────────────────────

class DashboardViewsTest(TestCase):

    def setUp(self):
        self.user = make_user("dash_user")
        self.client = DjangoClient()
        self.client.login(username="dash_user", password="testpass123")

    def _assert_page_ok(self, url_name):
        response = self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 200, f"Page '{url_name}' returned {response.status_code}")

    def test_dashboard_page(self):
        self._assert_page_ok("dashboard")

    def test_connected_accounts_page(self):
        self._assert_page_ok("connected_accounts")

    def test_automation_reels_page(self):
        self._assert_page_ok("automation_reels")

    def test_inbox_page(self):
        self._assert_page_ok("inbox")

    def test_crm_leads_page(self):
        self._assert_page_ok("crm_leads")

    def test_analytics_page(self):
        self._assert_page_ok("analytics")

    def test_broadcasts_page(self):
        self._assert_page_ok("broadcasts")

    def test_settings_page(self):
        self._assert_page_ok("settings")

    def test_content_calendar_page(self):
        self._assert_page_ok("content_calendar")

    def test_unauthenticated_redirects_to_login(self):
        anon_client = DjangoClient()
        response = anon_client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_login_page(self):
        anon_client = DjangoClient()
        response = anon_client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_signup_page(self):
        anon_client = DjangoClient()
        response = anon_client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_signup_creates_user_and_redirects(self):
        anon_client = DjangoClient()
        response = anon_client.post(reverse("signup"), {
            "username": "newuser123",
            "password1": "securePass!99",
            "password2": "securePass!99",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser123").exists())

    def test_logout_redirects(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)

    def test_landing_page_public(self):
        anon_client = DjangoClient()
        response = anon_client.get(reverse("landing_page"))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Database Integrity
# ─────────────────────────────────────────────────────────────────────────────

class DatabaseIntegrityTest(TestCase):

    def setUp(self):
        self.user = make_user("db_user")

    def test_instagram_account_id_unique(self):
        make_account(self.user, account_id="UNIQUE001")
        with self.assertRaises(Exception):
            make_account(self.user, account_id="UNIQUE001")

    def test_comment_id_unique(self):
        account = make_account(self.user, account_id="DBI001")
        InstagramComment.objects.create(
            account=account, comment_id="cmt_uniq", media_id="m1",
            username="u", text="t", timestamp=timezone.now()
        )
        with self.assertRaises(Exception):
            InstagramComment.objects.create(
                account=account, comment_id="cmt_uniq", media_id="m1",
                username="u2", text="t2", timestamp=timezone.now()
            )

    def test_message_id_unique(self):
        account = make_account(self.user, account_id="DBI002")
        conv = Conversation.objects.create(
            user=self.user, instagram_account=account,
            conversation_id="conv_dbi", participant_id="p",
            participant_username="p_user", platform="instagram"
        )
        Message.objects.create(
            conversation=conv, sender_type="participant",
            message_text="msg", message_id="msg_uniq", timestamp=timezone.now()
        )
        with self.assertRaises(Exception):
            Message.objects.create(
                conversation=conv, sender_type="participant",
                message_text="msg2", message_id="msg_uniq", timestamp=timezone.now()
            )

    def test_instagram_session_one_to_one(self):
        account = make_account(self.user, account_id="DBI003")
        InstagramSession.objects.create(account=account, session_json={"k": "v"})
        with self.assertRaises(Exception):
            InstagramSession.objects.create(account=account, session_json={"k2": "v2"})

    def test_cascade_delete_account_removes_comments(self):
        account = make_account(self.user, account_id="DBI004")
        InstagramComment.objects.create(
            account=account, comment_id="cmt_cas", media_id="m",
            username="u", text="t", timestamp=timezone.now()
        )
        account.delete()
        self.assertFalse(InstagramComment.objects.filter(comment_id="cmt_cas").exists())

    def test_cascade_delete_user_removes_account(self):
        user2 = make_user("db_user_del")
        make_account(user2, account_id="DBI005")
        user2.delete()
        self.assertFalse(InstagramAccount.objects.filter(account_id="DBI005").exists())

    def test_lead_creation_and_retrieval(self):
        lead = Lead.objects.create(user=self.user, name="Test Lead", source="instagram", status="new")
        LeadTimeline.objects.create(
            lead=lead, event_type="created", description="Created via test"
        )
        lead_from_db = Lead.objects.get(pk=lead.pk)
        self.assertEqual(lead_from_db.name, "Test Lead")
        self.assertEqual(lead_from_db.timeline.count(), 1)


# ─────────────────────────────────────────────────────────────────────────────
# 11. Security
# ─────────────────────────────────────────────────────────────────────────────

class SecurityTest(TestCase):

    def setUp(self):
        self.user = make_user("sec_user")
        self.authed = jwt_client(self.user)

    def test_xframe_options_header_present(self):
        client = DjangoClient()
        client.login(username="sec_user", password="testpass123")
        response = client.get("/dashboard/")
        self.assertIn("X-Frame-Options", response)

    def test_secrets_not_exposed_in_api(self):
        account = make_account(self.user, account_id="SEC001")
        InstagramSession.objects.create(
            account=account,
            session_json={"cookie": "secret_session_token_abc123"}
        )
        response = self.authed.get("/api/instagram/accounts/")
        data = response.json()
        self.assertNotIn("secret_session_token_abc123", str(data))

    def test_csrf_enforced_on_login_form(self):
        anon = DjangoClient(enforce_csrf_checks=True)
        response = anon.post("/login/", {
            "username": "sec_user",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 403)

    def test_other_user_cannot_access_my_leads(self):
        user_b = make_user("sec_user_b")
        Lead.objects.create(user=user_b, name="B's private lead", source="instagram", status="new")

        response = self.authed.get("/api/crm/leads/")
        data = response.json()
        names = [r["name"] for r in data.get("results", [])]
        self.assertNotIn("B's private lead", names)

    def test_other_user_cannot_access_my_conversations(self):
        user_b = make_user("sec_user_c")
        account_b = make_account(user_b, account_id="SECB001")
        Conversation.objects.create(
            user=user_b, instagram_account=account_b,
            conversation_id="secret_conv", participant_id="p",
            participant_username="secret", platform="instagram"
        )

        response = self.authed.get("/api/inbox/conversations/")
        data = response.json()
        conv_ids = [r.get("conversation_id") for r in data.get("results", [])]
        self.assertNotIn("secret_conv", conv_ids)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Configuration
# ─────────────────────────────────────────────────────────────────────────────

class ConfigurationTest(TestCase):

    def test_celery_broker_configured(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, "CELERY_BROKER_URL"))
        self.assertIsNotNone(settings.CELERY_BROKER_URL)

    def test_celery_beat_schedule_defined(self):
        from django.conf import settings
        self.assertIn("poll-instagram-comments-periodic", settings.CELERY_BEAT_SCHEDULE)
        self.assertIn("poll-instagram-dms-periodic", settings.CELERY_BEAT_SCHEDULE)

    def test_database_configured(self):
        from django.conf import settings
        self.assertIn("default", settings.DATABASES)
        self.assertEqual(settings.DATABASES["default"]["ENGINE"], "django.db.backends.postgresql")

    def test_rest_framework_uses_jwt(self):
        from django.conf import settings
        auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", [])
        jwt_class = "rest_framework_simplejwt.authentication.JWTAuthentication"
        self.assertIn(jwt_class, auth_classes)

    def test_installed_apps_complete(self):
        from django.conf import settings
        required = ["core", "instagram", "automation", "inbox", "crm", "analytics", "broadcasts"]
        for app in required:
            self.assertIn(app, settings.INSTALLED_APPS, f"App '{app}' missing from INSTALLED_APPS")

    def test_static_dirs_configured(self):
        from django.conf import settings
        self.assertIsNotNone(settings.STATIC_URL)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Contact Form (public API)
# ─────────────────────────────────────────────────────────────────────────────

class ContactFormTest(TestCase):

    def test_submit_contact_form(self):
        client = APIClient()
        response = client.post("/api/contact-form/", {
            "name": "Alice",
            "email": "alice@example.com",
            "message": "Hello from Alice",
        }, format="json")
        self.assertEqual(response.status_code, 201)

    def test_contact_form_missing_fields(self):
        client = APIClient()
        response = client.post("/api/contact-form/", {
            "name": "Alice",
        }, format="json")
        self.assertEqual(response.status_code, 400)


# ─────────────────────────────────────────────────────────────────────────────
# 14. Instagram Services — create_demo_account (KNOWN BUG TEST)
# ─────────────────────────────────────────────────────────────────────────────

class InstagramServiceTest(TestCase):

    def setUp(self):
        self.user = make_user("svc_user")

    def test_create_demo_account_missing_is_bug(self):
        """
        CRITICAL BUG: InstagramService.create_demo_account() is referenced in
        instagram/views.py (line 23) and templates/connected_accounts.html (line 116)
        but does NOT exist in instagram/services.py.
        The 'Connect Demo Account' button on the UI is 100% broken.
        This test should FAIL until the bug is fixed.
        """
        from instagram.services import InstagramService
        self.assertTrue(
            hasattr(InstagramService, "create_demo_account"),
            "CRITICAL BUG: InstagramService.create_demo_account() is missing!"
        )

    def test_get_instagram_client_delegates_to_session_manager(self):
        account = make_account(self.user, account_id="SVC001")
        from instagram.services import InstagramService
        with patch("instagram.services.SessionManager") as MockSM:
            mock_sm = MockSM.return_value
            mock_sm.ensure_session_active.return_value = MagicMock()
            InstagramService.get_instagram_client(account)
            MockSM.assert_called_once_with(account)
            mock_sm.ensure_session_active.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 15. Instagram Linking and Resilience Tests
# ─────────────────────────────────────────────────────────────────────────────

from instagram.exceptions import InstagramTwoFactorRequiredException

class InstagramLinkingAndResilienceTest(TestCase):

    def setUp(self):
        self.user = make_user("resilient_user")
        self.client = jwt_client(self.user)
        self.other_user = make_user("other_resilient_user")

    @patch("instagram.services.SessionManager")
    def test_connect_real_two_factor_required(self, MockSM):
        """ViewSet returns 202 status and two_factor_required status when 2FA is required."""
        mock_sm = MockSM.return_value
        mock_sm.login.side_effect = InstagramTwoFactorRequiredException("2FA required", two_factor_info={"obfuscated_phone": "123"})
        
        response = self.client.post("/api/instagram/accounts/connect_real/", {
            "username": "test_2fa_user",
            "password": "secretpassword"
        }, format="json")
        
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["status"], "two_factor_required")
        self.assertEqual(data["two_factor_info"], {"obfuscated_phone": "123"})

    @patch("instagram.services.SessionManager")
    def test_connect_real_challenge_required(self, MockSM):
        """ViewSet returns 202 status and challenge_required status when a login challenge occurs."""
        mock_sm = MockSM.return_value
        mock_sm.login.side_effect = InstagramChallengeException("Challenge needed", challenge_url="https://ig.com/ch")
        
        response = self.client.post("/api/instagram/accounts/connect_real/", {
            "username": "test_challenge_user",
            "password": "secretpassword"
        }, format="json")
        
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["status"], "challenge_required")
        self.assertEqual(data["challenge_url"], "https://ig.com/ch")

    def test_connect_real_prevent_cross_user_takeover(self):
        """ViewSet blocks user A from connecting user B's account."""
        # Create user B's account
        make_account(self.other_user, username="victim_user", account_id="ig_victim_user")
        
        # User A tries to link victim_user
        response = self.client.post("/api/instagram/accounts/connect_real/", {
            "username": "victim_user",
            "password": "somepassword"
        }, format="json")
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("already connected by another user", response.json()["error"])

    @patch("instagram.tasks.CommentListener")
    def test_poll_task_disconnects_on_login_required(self, MockListener):
        """Comment poll Celery task marks account as disconnected if LoginRequired occurs."""
        account = make_account(self.user, username="test_task_user", account_id="ig_test_task_user", status="connected")
        
        from instagrapi.exceptions import LoginRequired
        mock_list = MockListener.return_value
        mock_list.poll_account.side_effect = LoginRequired("session expired")
        
        from instagram.tasks import poll_single_account_comments
        poll_single_account_comments(account.id)
        
        account.refresh_from_db()
        self.assertEqual(account.status, "disconnected")

    @patch("instagram.action_tasks._dispatch_action")
    def test_action_task_disconnects_on_login_required(self, mock_dispatch):
        """Outbound action task disconnects account and marks action as DEAD_LETTER on auth error."""
        account = make_account(self.user, username="test_action_user", account_id="ig_test_action_user", status="connected")
        
        from instagram.action_models import ActionExecution
        action = ActionExecution.objects.create(
            instagram_account=account,
            action_type="SEND_DM",
            request_payload={"recipient_id": "123", "text": "hello"},
            status=ActionExecution.Status.PENDING
        )
        
        from instagrapi.exceptions import LoginRequired
        mock_dispatch.side_effect = LoginRequired("auth failure")
        
        from instagram.action_tasks import execute_action_task
        execute_action_task(action.execution_id)
        
        account.refresh_from_db()
        action.refresh_from_db()
        
        self.assertEqual(account.status, "disconnected")
        self.assertEqual(action.status, ActionExecution.Status.DEAD_LETTER)
        self.assertIn("Authentication failure", action.error_message)
