import logging
from automation.services import AutomationService
from automation.models import AutomationWorkflow
from .models import InstagramComment
from inbox.models import Message

logger = logging.getLogger(__name__)

class WorkflowBridge:
    @staticmethod
    def trigger_comment_workflow(comment: InstagramComment):
        """
        Translates InstagramComment into trigger data, checks for matching
        active workflows, and executes them.
        """
        try:
            workflows = AutomationWorkflow.objects.filter(
                user=comment.account.user,
                status='active',
                trigger_type='comment'
            )
            
            triggered_any = False
            for workflow in workflows:
                trigger_config = workflow.trigger_config or {}
                keyword = trigger_config.get('keyword', '').lower()
                comment_text = comment.text or ''
                
                # If workflow is linked to a specific reel, it must match the comment's media_id
                if workflow.reel_id is not None:
                    if workflow.reel.reel_id != comment.media_id:
                        continue
                
                if keyword == '' or keyword in comment_text.lower():
                    trigger_data = {
                        'platform': 'instagram',
                        'account_id': comment.account.account_id,
                        'account_pk': comment.account.id,
                        'comment_id': comment.comment_id,
                        'comment_text': comment_text,
                        'username': comment.username,
                        'media_id': comment.media_id
                    }
                    logger.info(f"Triggering workflow '{workflow.name}' for comment {comment.comment_id}")
                    AutomationService.execute_workflow(workflow, trigger_data)
                    triggered_any = True
            
            # Mark processed as True if it matched any workflows (or just mark processed anyway)
            comment.processed = True
            comment.save()
            return triggered_any
        except Exception as e:
            logger.error(f"Error in WorkflowBridge for comment {comment.comment_id}: {e}", exc_info=True)
            return False

    @staticmethod
    def trigger_message_workflow(message: Message):
        """
        Translates a Message into standardized trigger data, checks for matching
        active workflows (trigger_type='message' or 'instagram_dm'), and executes them.
        """
        try:
            instagram_account = message.conversation.instagram_account
            user = message.conversation.user
            
            # Match either 'message' or 'instagram_dm' trigger type
            workflows = AutomationWorkflow.objects.filter(
                user=user,
                status='active',
                trigger_type__in=['message', 'instagram_dm']
            )
            
            triggered_any = False
            for workflow in workflows:
                trigger_config = workflow.trigger_config or {}
                keyword = trigger_config.get('keyword', '').lower()
                message_text = message.message_text or ''
                
                # Run if keyword matches or if trigger has no keyword config
                if keyword == '' or keyword in message_text.lower():
                    trigger_data = {
                        'platform': 'instagram',
                        'account_id': instagram_account.account_id if instagram_account else None,
                        'account_pk': instagram_account.id if instagram_account else None,
                        'conversation_id': message.conversation.conversation_id,
                        'message_id': message.message_id,
                        'sender_id': message.sender_id,
                        'sender_username': message.sender_username,
                        'recipient_account': instagram_account.username if instagram_account else None,
                        'message_type': message.message_type,
                        'message_text': message_text,
                        'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                        'attachment_metadata': {
                            'message_type': message.message_type
                        },
                        'raw_payload': message.raw_payload
                    }
                    logger.info(f"Triggering workflow '{workflow.name}' for message {message.message_id}")
                    AutomationService.execute_workflow(workflow, trigger_data)
                    triggered_any = True
            
            message.processed = True
            message.save()
            return triggered_any
        except Exception as e:
            logger.error(f"Error in WorkflowBridge for message {message.message_id}: {e}", exc_info=True)
            return False

