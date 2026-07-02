

import os
import json
import time
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from instagrapi import Client
from instagrapi.exceptions import (BadPassword, ChallengeRequired, TwoFactorRequired, 
                                   FeedbackRequired, PleaseWaitFewMinutes, LoginRequired)

from .models import InstagramAccount, InstagramSession
from .exceptions import InstagramException, InstagramRateLimitException, InstagramChallengeException

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages Instagram sessions, including login, persistence, and refresh."""

    def __init__(self, account: InstagramAccount):
        self.account = account
        self.cl = Client()
        self._load_session()

    def _load_session(self):
        """Loads the session from the database if it exists and is valid."""
        try:
            session_obj = InstagramSession.objects.get(account=self.account)
            self.cl.set_settings(session_obj.session_json)
            logger.info(f"Loaded session for {self.account.username} from database.")
        except ObjectDoesNotExist:
            logger.info(f"No session found in database for {self.account.username}.")
        except Exception as e:
            logger.warning(f"Failed to load session for {self.account.username}: {e}")

    def _save_session(self):
        """Saves the current session to the database."""
        session_json = self.cl.get_settings()
        session_obj, created = InstagramSession.objects.update_or_create(
            account=self.account,
            defaults={'session_json': session_json}
        )
        if created:
            logger.info(f"Created new session in database for {self.account.username}.")
        else:
            logger.info(f"Updated existing session in database for {self.account.username}.")

    def login(self, username, password, verification_code=None) -> bool:
        """Logs into Instagram and saves the session."""
        try:
            settings = self.cl.get_settings()
            if settings.get('authorization_data'): # Check if already logged in with loaded session
                logger.info(f"Already logged in as {self.account.username}.")
                self.account.status = 'connected'
                self.account.last_sync = timezone.now()
                self.account.save()
                return True

            self.cl.login(username, password, verification_code=verification_code)
            self._save_session()
            self.account.status = 'connected'
            self.account.last_sync = timezone.now()
            self.account.save()
            logger.info(f"Successfully logged in as {self.account.username}.")
            return True
        except BadPassword:
            logger.error(f"Invalid credentials for {self.account.username}.")
            self.account.status = 'disconnected'
            self.account.save()
            raise InstagramException("Invalid Instagram credentials.")
        except ChallengeRequired as e:
            logger.warning(f"Challenge required for {self.account.username}. {e}")
            self.account.status = 'pending'
            self.account.save()
            # You might need to implement a mechanism to ask the user for challenge resolution
            raise InstagramChallengeException(f"Instagram challenge required. Please log into the Instagram app on your phone to approve the login attempt, then try again.")
        except TwoFactorRequired:
            logger.warning(f"Two-factor authentication required for {self.account.username}.")
            self.account.status = 'pending'
            self.account.save()
            raise InstagramException("Two-factor authentication required.")
        except FeedbackRequired as e:
            logger.warning(f"Feedback required for {self.account.username}: {e}")
            self.account.status = 'disconnected'
            self.account.save()
            raise InstagramException(f"Instagram feedback required: {e}")
        except PleaseWaitFewMinutes as e:
            logger.warning(f"Please wait a few minutes for {self.account.username}: {e}")
            raise InstagramRateLimitException(f"Instagram rate limit: {e}")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during login for {self.account.username}: {e}")
            self.account.status = 'disconnected'
            self.account.save()
            raise InstagramException(f"Login failed: {e}")

    def logout(self):
        """Logs out from Instagram and clears the session."""
        try:
            self.cl.logout()
            try:
                session_obj = InstagramSession.objects.get(account=self.account)
                session_obj.delete()
                logger.info(f"Deleted session from database for {self.account.username}.")
            except ObjectDoesNotExist:
                logger.info(f"No session found in database to delete for {self.account.username}.")
            self.account.status = 'disconnected'
            self.account.save()
            logger.info(f"Successfully logged out {self.account.username}.")
        except Exception as e:
            logger.error(f"Error during logout for {self.account.username}: {e}")
            raise InstagramException(f"Logout failed: {e}")

    def refresh_session(self) -> bool:
        """Refreshes the Instagram session if needed."""
        settings = self.cl.get_settings()
        if not settings.get('authorization_data'):
            logger.info(f"Session for {self.account.username} is not active, attempting re-login.")
            # Attempt re-login using stored credentials or a refresh token mechanism
            # For now, we'll assume credentials are available via environment variables or a secure store
            # In a real scenario, you'd fetch these securely.
            username = os.environ.get(f'INSTAGRAM_USERNAME_{self.account.pk}') # Example
            password = os.environ.get(f'INSTAGRAM_PASSWORD_{self.account.pk}') # Example
            if username and password:
                return self.login(username, password)
            else:
                logger.warning(f"Credentials not found for {self.account.username} to re-login.")
                self.account.status = 'disconnected'
                self.account.save()
                return False
        
        # instagrapi handles session refresh internally when making requests
        # We just need to ensure the client is logged in.
        logger.info(f"Session for {self.account.username} is active and does not require explicit refresh.")
        self.account.last_sync = timezone.now()
        self.account.save()
        return True

    def ensure_session_active(self) -> Client:
        """Ensures the session is active and returns the instagrapi client."""
        settings = self.cl.get_settings()
        if not settings.get('authorization_data'):
            logger.info(f"Session for {self.account.username} is not active, attempting to refresh.")
            if not self.refresh_session():
                raise InstagramException(f"Failed to activate session for {self.account.username}.")
        return self.cl

    def get_client(self) -> Client:
        """Returns the instagrapi client instance."""
        return self.cl

    @staticmethod
    def get_session_manager(account_id: int) -> 'SessionManager':
        """Factory method to get a SessionManager instance for an account."""
        try:
            account = InstagramAccount.objects.get(pk=account_id)
            return SessionManager(account)
        except ObjectDoesNotExist:
            raise InstagramException(f"InstagramAccount with ID {account_id} not found.")


# Placeholder for custom exceptions
# These would typically be in instagram/exceptions.py
