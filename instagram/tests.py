from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import MagicMock, patch
from django.utils import timezone
from instagram.models import InstagramAccount, InstagramComment
from instagram.comment_listener import CommentListener
from instagram.workflow_bridge import WorkflowBridge
from automation.models import AutomationWorkflow

class InstagramCommentPollTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.account = InstagramAccount.objects.create(
            user=self.user,
            username="test_insta_handle",
            account_id="12345",
            status="connected"
        )
        self.workflow = AutomationWorkflow.objects.create(
            user=self.user,
            name="Price Responder",
            status="active",
            trigger_type="comment",
            trigger_config={"keyword": "price"}
        )

    @patch('instagram.comment_listener.InstagramService.get_instagram_client')
    def test_poll_real_account_saves_and_triggers(self, mock_get_client):
        # Setup mocks
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.user_id_from_username.return_value = "insta_user_id_999"
        
        # Mock recent media
        mock_media = MagicMock()
        mock_media.pk = "media_789"
        mock_client.user_medias.return_value = [mock_media]
        
        # Mock comments
        mock_comment = MagicMock()
        mock_comment.pk = "comment_abc"
        mock_comment.text = "How much is the price?"
        mock_comment.user.username = "some_commenter"
        mock_comment.created_at = timezone.now()
        mock_client.media_comments.return_value = [mock_comment]
        
        # Run poll
        listener = CommentListener(self.account)
        count = listener.poll_account()
        
        # Assertions
        self.assertEqual(count, 1)
        
        # Verify InstagramComment was created
        created_comment = InstagramComment.objects.get(comment_id="comment_abc")
        self.assertEqual(created_comment.text, "How much is the price?")
        self.assertEqual(created_comment.username, "some_commenter")
        self.assertTrue(created_comment.processed)
        
    @patch('instagram.workflow_bridge.AutomationService.execute_workflow')
    def test_workflow_bridge_keyword_matching(self, mock_execute_workflow):
        # Create non-matching comment
        comment1 = InstagramComment.objects.create(
            account=self.account,
            comment_id="c1",
            media_id="m1",
            username="user1",
            text="Just saying hi!",
            timestamp=timezone.now(),
            processed=False
        )
        WorkflowBridge.trigger_comment_workflow(comment1)
        mock_execute_workflow.assert_not_called()
        self.assertTrue(comment1.processed)
        
        # Create matching comment
        comment2 = InstagramComment.objects.create(
            account=self.account,
            comment_id="c2",
            media_id="m1",
            username="user2",
            text="what is the PRICE?",
            timestamp=timezone.now(),
            processed=False
        )
        WorkflowBridge.trigger_comment_workflow(comment2)
        mock_execute_workflow.assert_called_once()
        self.assertTrue(comment2.processed)

from inbox.models import Conversation, Message
from instagram.dm_listener import DMListener

class InstagramDMPollTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dmuser", password="password")
        self.account = InstagramAccount.objects.create(
            user=self.user,
            username="test_dm_handle",
            account_id="54321",
            status="connected"
        )
        self.workflow = AutomationWorkflow.objects.create(
            user=self.user,
            name="Message Keyword Responder",
            status="active",
            trigger_type="message",
            trigger_config={"keyword": "info"}
        )

    @patch('instagram.dm_listener.InstagramService.get_instagram_client')
    @patch('instagram.workflow_bridge.AutomationService.execute_workflow')
    def test_poll_real_inbox_saves_and_triggers(self, mock_execute_workflow, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.user_id = "our_insta_user_id"
        
        # Mock active threads
        mock_user = MagicMock()
        mock_user.pk = "participant_user_1"
        mock_user.username = "sender_alice"
        
        mock_thread = MagicMock()
        mock_thread.id = "thread_id_xyz"
        mock_thread.users = [mock_user]
        mock_client.direct_threads.return_value = [mock_thread]
        
        # Mock direct messages
        mock_msg = MagicMock()
        mock_msg.id = "msg_id_777"
        mock_msg.user_id = "participant_user_1"
        mock_msg.item_type = "text"
        mock_msg.text = "Can I get some info please?"
        mock_msg.timestamp = timezone.now()
        mock_msg.dict.return_value = {"id": "msg_id_777", "text": "Can I get some info please?"}
        
        mock_client.direct_messages.return_value = [mock_msg]
        
        # Run DM listener poll
        listener = DMListener(self.account)
        count = listener.poll_inbox()
        
        # Assertions
        self.assertEqual(count, 1)
        
        # Check DB Conversation and Message
        conv = Conversation.objects.get(conversation_id="thread_id_xyz")
        self.assertEqual(conv.participant_username, "sender_alice")
        
        msg = Message.objects.get(message_id="msg_id_777")
        self.assertEqual(msg.message_text, "Can I get some info please?")
        self.assertEqual(msg.sender_username, "sender_alice")
        self.assertEqual(msg.sender_type, "participant")
        self.assertTrue(msg.processed)
        
        # Verify workflow executed due to matching keyword 'info'
        mock_execute_workflow.assert_called_once()

    @patch('instagram.dm_listener.InstagramService.get_instagram_client')
    @patch('instagram.workflow_bridge.AutomationService.execute_workflow')
    def test_duplicate_message_prevention(self, mock_execute_workflow, mock_get_client):
        # Pre-seed Conversation and Message in DB
        conv = Conversation.objects.create(
            user=self.user,
            instagram_account=self.account,
            conversation_id="thread_id_dup",
            participant_id="participant_user_dup",
            participant_username="sender_dup",
            platform="instagram"
        )
        Message.objects.create(
            conversation=conv,
            sender_type="participant",
            sender_id="participant_user_dup",
            sender_username="sender_dup",
            message_text="This was already processed",
            message_id="msg_id_dup",
            timestamp=timezone.now(),
            processed=True
        )
        
        # Mock client to return the duplicate message
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.user_id = "our_insta_user_id"
        
        mock_user = MagicMock()
        mock_user.pk = "participant_user_dup"
        mock_user.username = "sender_dup"
        
        mock_thread = MagicMock()
        mock_thread.id = "thread_id_dup"
        mock_thread.users = [mock_user]
        mock_client.direct_threads.return_value = [mock_thread]
        
        mock_msg = MagicMock()
        mock_msg.id = "msg_id_dup"
        mock_msg.user_id = "participant_user_dup"
        mock_msg.item_type = "text"
        mock_msg.text = "This was already processed"
        mock_msg.timestamp = timezone.now()
        
        mock_client.direct_messages.return_value = [mock_msg]
        
        listener = DMListener(self.account)
        count = listener.poll_inbox()
        
        # Should detect 0 new messages
        self.assertEqual(count, 0)
        mock_execute_workflow.assert_not_called()

