import uuid
from django.utils import timezone
from datetime import timedelta
from .models import InstagramAccount, InstagramReel, CommentLog, DMLog, InstagramSession
from .session_manager import SessionManager
from .exceptions import (
    InstagramException, InstagramRateLimitException, InstagramChallengeException,
    InstagramTwoFactorRequiredException
)
import logging

logger = logging.getLogger(__name__)

DEMO_REELS = [
    {"reel_id": "demo_reel_001", "title": "Product Launch Reel"},
    {"reel_id": "demo_reel_002", "title": "Tutorial Highlights"},
    {"reel_id": "demo_reel_003", "title": "Behind the Scenes"},
]


class InstagramService:
    """Service layer for Instagram operations, interacting with instagrapi."""

    @staticmethod
    def create_demo_account(user) -> InstagramAccount:
        """
        Creates (or retrieves) a demo Instagram account for the given user.
        The account is pre-seeded with mock reels so the dashboard is immediately
        usable without any real Instagram credentials.
        """
        # Use a deterministic account_id so duplicate clicks are idempotent
        demo_account_id = f"demo_{user.pk}"

        account, created = InstagramAccount.objects.get_or_create(
            account_id=demo_account_id,
            defaults={
                "user": user,
                "username": f"demo_user_{user.pk}",
                "status": "demo",
                "is_demo": True,
                "automation_status": True,
                "last_sync": timezone.now(),
            },
        )

        if created:
            # Seed demo reels with user-scoped IDs to avoid unique constraint violations
            demo_reels = [
                {"reel_id": f"demo_{user.pk}_reel_001", "title": "Product Launch Reel"},
                {"reel_id": f"demo_{user.pk}_reel_002", "title": "Tutorial Highlights"},
                {"reel_id": f"demo_{user.pk}_reel_003", "title": "Behind the Scenes"},
            ]
            for reel_data in demo_reels:
                InstagramReel.objects.get_or_create(
                    reel_id=reel_data["reel_id"],
                    defaults={"account": account, "title": reel_data["title"]},
                )
            logger.info(f"Created demo account for user {user.username} (account_id={demo_account_id})")
        else:
            logger.info(f"Returned existing demo account for user {user.username}")

        # Always ensure demo reels exist (handles existing accounts with missing reels)
        if not account.reels.exists():
            demo_reels = [
                {"reel_id": f"demo_{user.pk}_reel_001", "title": "Product Launch Reel"},
                {"reel_id": f"demo_{user.pk}_reel_002", "title": "Tutorial Highlights"},
                {"reel_id": f"demo_{user.pk}_reel_003", "title": "Behind the Scenes"},
            ]
            for reel_data in demo_reels:
                InstagramReel.objects.get_or_create(
                    reel_id=reel_data["reel_id"],
                    defaults={"account": account, "title": reel_data["title"]},
                )
            logger.info(f"Seeded demo reels for user {user.username}")

        return account

    @staticmethod
    def login_instagram_account(account: InstagramAccount, username, password, verification_code=None):
        """Logs into an Instagram account and handles session management."""
        session_manager = SessionManager(account)
        try:
            session_manager.login(username, password, verification_code)
            account.status = 'connected'
            account.last_sync = timezone.now()
            account.save()
            return True
        except InstagramTwoFactorRequiredException as e:
            account.status = 'pending'
            account.save()
            logger.warning(f"Instagram 2FA required for {account.username}")
            raise
        except InstagramChallengeException as e:
            account.status = 'pending'
            account.save()
            logger.warning(f"Instagram challenge required for {account.username}: {e.challenge_url}")
            raise
        except InstagramException as e:
            account.status = 'disconnected'
            account.save()
            logger.error(f"Login failed for {account.username}: {e}")
            raise

    @staticmethod
    def logout_instagram_account(account: InstagramAccount):
        """Logs out from an Instagram account and clears the session."""
        session_manager = SessionManager(account)
        try:
            session_manager.logout()
            account.status = 'disconnected'
            account.save()
            return True
        except InstagramException as e:
            logger.error(f"Logout failed for {account.username}: {e}")
            raise

    @staticmethod
    def get_instagram_client(account: InstagramAccount):
        """Returns an active instagrapi client for the given account."""
        session_manager = SessionManager(account)
        return session_manager.ensure_session_active()

    @staticmethod
    def sync_reels(account: InstagramAccount):
        """Fetches reels from Instagram using instagrapi and saves them locally."""
        if account.is_demo:
            # Seed demo reels with user-scoped IDs if not done already
            if not account.reels.exists():
                user = account.user
                demo_reels = [
                    {"reel_id": f"demo_{user.pk}_reel_001", "title": "Product Launch Reel"},
                    {"reel_id": f"demo_{user.pk}_reel_002", "title": "Tutorial Highlights"},
                    {"reel_id": f"demo_{user.pk}_reel_003", "title": "Behind the Scenes"},
                ]
                for reel_data in demo_reels:
                    InstagramReel.objects.get_or_create(
                        reel_id=reel_data["reel_id"],
                        defaults={"account": account, "title": reel_data["title"]}
                    )
            return

        client = InstagramService.get_instagram_client(account)
        user_id = client.user_id_from_username(account.username)
        
        # Fetch user's recent media
        medias = client.user_medias(user_id, amount=20)
        
        for media in medias:
            # We filter for videos or reels (media_type = 2 is video in Instagram API)
            # Or we can import all media posts as targetable for triggers
            InstagramReel.objects.update_or_create(
                reel_id=str(media.pk),
                defaults={
                    'account': account,
                    'title': media.caption_text or f"Post {media.pk}",
                    'thumbnail_url': str(media.thumbnail_url) if media.thumbnail_url else None,
                    'permalink': media.resources[0].video_url if media.resources else getattr(media, 'video_url', None) or media.thumbnail_url
                }
            )


    

