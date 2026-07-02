import random
import time
import logging
from django.utils import timezone
from .models import InstagramAccount, InstagramComment
from .services import InstagramService
from .utils import (
    MAX_MEDIA_FETCH,
    MAX_COMMENT_FETCH,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
)
from .workflow_bridge import WorkflowBridge

logger = logging.getLogger(__name__)

class CommentListener:
    def __init__(self, account: InstagramAccount):
        self.account = account
        self.client = None

    def _get_client(self):
        if not self.client and not self.account.is_demo:
            self.client = InstagramService.get_instagram_client(self.account)
        return self.client

    def poll_account(self):
        """
        Polls Instagram for comments on the account's recent media.
        """
        logger.info(f"Starting comment polling for account: {self.account.username} (Demo: {self.account.is_demo})")
        if self.account.is_demo:
            return self._poll_demo_account()
        else:
            return self._poll_real_account()

    def _poll_real_account(self):
        client = self._get_client()
        try:
            # 1. Fetch user ID
            user_id = client.user_id_from_username(self.account.username)
            # 2. Fetch recent media
            medias = client.user_medias(user_id, amount=MAX_MEDIA_FETCH)
            
            new_comments_count = 0
            
            for media in medias:
                # Add delay to avoid rate limit
                time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))
                
                # Fetch comments
                comments = client.media_comments(media.pk, amount=MAX_COMMENT_FETCH)
                
                for comment in comments:
                    comment_id = str(comment.pk)
                    # Check if already processed
                    if not InstagramComment.objects.filter(comment_id=comment_id).exists():
                        # Create generic InstagramComment
                        inst_comment = InstagramComment.objects.create(
                            account=self.account,
                            comment_id=comment_id,
                            media_id=str(media.pk),
                            username=comment.user.username,
                            text=comment.text,
                            timestamp=getattr(comment, 'created_at_utc', getattr(comment, 'created_at', timezone.now())),
                            processed=False
                        )
                        # Trigger workflow via bridge
                        WorkflowBridge.trigger_comment_workflow(inst_comment)
                        new_comments_count += 1
                        
            logger.info(f"Finished polling for {self.account.username}. Found {new_comments_count} new comments.")
            return new_comments_count
        except Exception as e:
            logger.error(f"Error polling real Instagram account {self.account.username}: {e}", exc_info=True)
            raise

    def _poll_demo_account(self):
        # In demo mode, we simulate fetching recent media and comments
        demo_usernames = ["alex_trend", "sophie_growth", "builder_bob", "marketing_guru", "tech_junkie"]
        demo_comments = [
            "This is amazing! Can you send me the link?",
            "Interested in this, please DM me info!",
            "Wow, very cool setup. How much does it cost?",
            "Can I get a discount code?",
            "Just sent you a message, check DMs!",
            "Love the reels, keep them coming!",
        ]
        
        num_new = random.randint(1, 2)
        new_comments_count = 0
        
        for _ in range(num_new):
            comment_id = f"demo_comment_{random.randint(100000, 999999)}"
            media_id = f"demo_media_{random.randint(1, 5)}"
            username = random.choice(demo_usernames)
            text = random.choice(demo_comments)
            
            inst_comment = InstagramComment.objects.create(
                account=self.account,
                comment_id=comment_id,
                media_id=media_id,
                username=username,
                text=text,
                timestamp=timezone.now(),
                processed=False
            )
            WorkflowBridge.trigger_comment_workflow(inst_comment)
            new_comments_count += 1
            
        logger.info(f"Simulated polling for demo account {self.account.username}. Generated {new_comments_count} new comments.")
        return new_comments_count
