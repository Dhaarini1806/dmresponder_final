import json
import random
import time
import logging
from django.utils import timezone
from django.db import transaction
from inbox.models import Conversation, Message
from .models import InstagramAccount
from .services import InstagramService
from .utils import (
    MAX_CONVERSATIONS,
    MAX_MESSAGES_PER_CONVERSATION,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)
from .workflow_bridge import WorkflowBridge

logger = logging.getLogger(__name__)

class DMListener:
    def __init__(self, account: InstagramAccount):
        self.account = account
        self.client = None

    def _get_client(self):
        if not self.client and not self.account.is_demo:
            self.client = InstagramService.get_instagram_client(self.account)
        return self.client

    def poll_inbox(self):
        """
        Polls Instagram Direct Inbox for new threads and messages.
        """
        logger.info(f"Starting DM inbox polling for account: {self.account.username} (Demo: {self.account.is_demo})")
        if self.account.is_demo:
            return self._poll_demo_inbox()
        else:
            return self._poll_real_inbox()

    def _poll_real_inbox(self):
        client = self._get_client()
        new_messages_count = 0
        try:
            # 1. Fetch active direct threads
            threads = client.direct_threads(amount=MAX_CONVERSATIONS)
            
            for thread in threads:
                # Add delay to avoid rate limiting
                time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
                
                thread_id = str(thread.id)
                
                # Extract participants
                participants = []
                participant_usernames = []
                participant_ids = []
                for user in thread.users:
                    try:
                        full_name = str(user.full_name or '')
                    except Exception:
                        full_name = ''
                    participants.append({
                        'id': str(user.pk),
                        'username': user.username,
                        'full_name': full_name
                    })
                    participant_usernames.append(user.username)
                    participant_ids.append(str(user.pk))
                
                # Determine primary participant details (for single user chat)
                primary_username = ", ".join(participant_usernames) if len(participant_usernames) > 1 else (participant_usernames[0] if participant_usernames else 'Unknown')
                primary_id = ", ".join(participant_ids) if len(participant_ids) > 1 else (participant_ids[0] if participant_ids else 'Unknown')
                
                # Find or create Conversation
                with transaction.atomic():
                    conv, created = Conversation.objects.update_or_create(
                        conversation_id=thread_id,
                        defaults={
                            'user': self.account.user,
                            'instagram_account': self.account,
                            'participant_id': primary_id,
                            'participant_username': primary_username,
                            'participants': participants,
                            'platform': 'instagram',
                            'is_read': False,
                        }
                    )
                
                if created:
                    logger.info(f"Discovered new conversation: {thread_id} with {primary_username}")

                # 2. Fetch latest messages for thread
                messages = client.direct_messages(thread_id, amount=MAX_MESSAGES_PER_CONVERSATION)
                
                for msg in messages:
                    msg_id = str(msg.id)
                    
                    # Skip duplicate messages
                    if Message.objects.filter(message_id=msg_id).exists():
                        continue
                    
                    item_type = msg.item_type
                    text = msg.text or ''
                    
                    # Determine sender type
                    is_me = str(msg.user_id) == str(client.user_id)
                    sender_type = 'user' if is_me else 'participant'
                    
                    # Find sender username
                    sender_username = self.account.username if is_me else 'Unknown'
                    for p in participants:
                        if p['id'] == str(msg.user_id):
                            sender_username = p['username']
                            break
                    
                    # Extract raw payload safely
                    raw_payload = {}
                    try:
                        raw_payload = json.loads(msg.model_dump_json())
                    except Exception:
                        raw_payload = {}
                    
                    # Save Message to DB
                    with transaction.atomic():
                        db_msg = Message.objects.create(
                            conversation=conv,
                            sender_type=sender_type,
                            sender_id=str(msg.user_id),
                            sender_username=sender_username,
                            message_text=text,
                            message_id=msg_id,
                            message_type=item_type,
                            timestamp=msg.timestamp or timezone.now(),
                            processed=False,
                            raw_payload=raw_payload
                        )
                        
                        conv.last_message = text or f"[{item_type} attachment]"
                        conv.last_message_timestamp = msg.timestamp
                        conv.save()
                    
                    logger.info(f"New message detected: {msg_id} in conversation {thread_id} from {sender_username}")
                    
                    # If incoming message, trigger workflow via bridge
                    if sender_type == 'participant':
                        WorkflowBridge.trigger_message_workflow(db_msg)
                        new_messages_count += 1
                        
            logger.info(f"Finished polling inbox for {self.account.username}. Detected {new_messages_count} new messages.")
            return new_messages_count
            
        except Exception as e:
            logger.error(f"Error polling Instagram DM for account {self.account.username}: {e}", exc_info=True)
            raise

    def _poll_demo_inbox(self):
        # Simulation for Demo accounts
        demo_threads = [
            {"id": "demo_thread_1", "username": "alice_smith", "user_id": "999001"},
            {"id": "demo_thread_2", "username": "bob_jones", "user_id": "999002"},
            {"id": "demo_thread_3", "username": "charlie_group", "participants": [
                {"id": "999003", "username": "charlie_brown"},
                {"id": "999004", "username": "snoopy"}
            ]}
        ]
        
        thread_data = random.choice(demo_threads)
        thread_id = thread_data["id"]
        
        if "participants" in thread_data:
            participants = thread_data["participants"]
            primary_username = ", ".join([p["username"] for p in participants])
            primary_id = ", ".join([p["id"] for p in participants])
        else:
            participants = [{
                "id": thread_data["user_id"],
                "username": thread_data["username"],
                "full_name": thread_data["username"].replace("_", " ").title()
            }]
            primary_username = thread_data["username"]
            primary_id = thread_data["user_id"]
            
        with transaction.atomic():
            conv, created = Conversation.objects.update_or_create(
                conversation_id=thread_id,
                defaults={
                    'user': self.account.user,
                    'instagram_account': self.account,
                    'participant_id': primary_id,
                    'participant_username': primary_username,
                    'participants': participants,
                    'platform': 'instagram',
                    'is_read': False,
                }
            )
            
        demo_texts = [
            "Hi there!",
            "I have a question about your services",
            "Can you tell me more about the price?",
            "Do you offer discounts?",
            "Check out this story reply!",
            "Sent an attachment"
        ]
        
        new_messages_count = 0
        num_msgs = random.randint(1, 2)
        for _ in range(num_msgs):
            msg_id = f"demo_msg_{random.randint(1000000, 9999999)}"
            text = random.choice(demo_texts)
            
            msg_type = 'text'
            if "attachment" in text:
                msg_type = 'media'
            elif "story" in text:
                msg_type = 'story_share'
                
            sender = random.choice(participants)
            
            with transaction.atomic():
                db_msg = Message.objects.create(
                    conversation=conv,
                    sender_type='participant',
                    sender_id=sender["id"],
                    sender_username=sender["username"],
                    message_text=text,
                    message_id=msg_id,
                    message_type=msg_type,
                    timestamp=timezone.now(),
                    processed=False,
                    raw_payload={"demo": True, "text": text, "type": msg_type}
                )
                
                conv.last_message = text
                conv.last_message_timestamp = db_msg.timestamp
                conv.save()
                
            WorkflowBridge.trigger_message_workflow(db_msg)
            new_messages_count += 1
            
        logger.info(f"Simulated polling for demo DM account {self.account.username}. Generated {new_messages_count} new messages.")
        return new_messages_count
