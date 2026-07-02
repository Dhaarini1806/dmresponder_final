import os
from django.conf import settings

COMMENT_POLL_INTERVAL = getattr(settings, 'COMMENT_POLL_INTERVAL', int(os.environ.get('COMMENT_POLL_INTERVAL', 60)))
MAX_MEDIA_FETCH = getattr(settings, 'MAX_MEDIA_FETCH', int(os.environ.get('MAX_MEDIA_FETCH', 5)))
MAX_COMMENT_FETCH = getattr(settings, 'MAX_COMMENT_FETCH', int(os.environ.get('MAX_COMMENT_FETCH', 20)))
RETRY_LIMIT = getattr(settings, 'RETRY_LIMIT', int(os.environ.get('RETRY_LIMIT', 3)))
REQUEST_DELAY_MIN = getattr(settings, 'REQUEST_DELAY_MIN', float(os.environ.get('REQUEST_DELAY_MIN', 1.0)))
REQUEST_DELAY_MAX = getattr(settings, 'REQUEST_DELAY_MAX', float(os.environ.get('REQUEST_DELAY_MAX', 3.0)))
BACKOFF_MULTIPLIER = getattr(settings, 'BACKOFF_MULTIPLIER', float(os.environ.get('BACKOFF_MULTIPLIER', 2.0)))

DM_POLL_INTERVAL = getattr(settings, 'DM_POLL_INTERVAL', int(os.environ.get('DM_POLL_INTERVAL', 20)))
MAX_CONVERSATIONS = getattr(settings, 'MAX_CONVERSATIONS', int(os.environ.get('MAX_CONVERSATIONS', 20)))
MAX_MESSAGES_PER_CONVERSATION = getattr(settings, 'MAX_MESSAGES_PER_CONVERSATION', int(os.environ.get('MAX_MESSAGES_PER_CONVERSATION', 20)))

