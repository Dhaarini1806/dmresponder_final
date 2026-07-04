import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class MetaGraphService:
    """Service to interact with the Official Meta Graph API (Instagram Messenger API)"""
    
    BASE_URL = f"https://graph.facebook.com/{getattr(settings, 'META_GRAPH_VERSION', 'v20.0')}"
    
    @classmethod
    def send_dm(cls, recipient_id, message_text, access_token):
        """Sends a Direct Message using the Instagram Messenger API"""
        url = f"{cls.BASE_URL}/me/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": message_text}
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully sent Meta DM to {recipient_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Meta DM to {recipient_id}: {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    @classmethod
    def fetch_reels(cls, instagram_account_id, access_token):
        """Fetches Reels/Media for an Instagram Professional Account"""
        url = f"{cls.BASE_URL}/{instagram_account_id}/media"
        params = {
            "fields": "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url",
            "access_token": access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json().get('data', [])
            reels = [item for item in data if item.get('media_type') == 'VIDEO']
            logger.info(f"Fetched {len(reels)} reels for account {instagram_account_id}")
            return reels
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch reels for {instagram_account_id}: {e}")
            if e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
            
    @classmethod
    def get_instagram_account_id(cls, page_id, access_token):
        """Gets the linked Instagram Professional Account ID for a Facebook Page"""
        url = f"{cls.BASE_URL}/{page_id}"
        params = {
            "fields": "instagram_business_account",
            "access_token": access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            ig_account_id = data.get('instagram_business_account', {}).get('id')
            return ig_account_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get IG account ID for page {page_id}: {e}")
            raise
