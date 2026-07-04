import logging
from celery import shared_task
from django.db.models import Q
from instagrapi.exceptions import LoginRequired
from .models import InstagramAccount
from .comment_listener import CommentListener
from .exceptions import InstagramRateLimitException, InstagramException
from .utils import RETRY_LIMIT, BACKOFF_MULTIPLIER

logger = logging.getLogger(__name__)
# Background tasks for Meta Graph API integration
