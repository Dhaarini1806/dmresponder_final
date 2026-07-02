from django.db import models
from django.contrib.auth.models import User

class InstagramAccount(models.Model):
    """Model for Instagram accounts connected to DMResponder"""
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('pending', 'Pending'),
        ('demo', 'Demo Mode'),
        ('disconnected', 'Disconnected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='instagram_accounts')
    username = models.CharField(max_length=255)
    profile_picture = models.URLField(null=True, blank=True)
    account_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_demo = models.BooleanField(default=False)
    last_sync = models.DateTimeField(null=True, blank=True)
    automation_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.status})"

class FacebookPage(models.Model):
    """Model for Facebook Pages connected to DMResponder"""
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='facebook_pages')
    name = models.CharField(max_length=255)
    page_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connected')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.page_id})"

class WhatsAppAccount(models.Model):
    """Model for WhatsApp accounts connected to DMResponder"""
    STATUS_CHOICES = [
        ('connected', 'Connected'),
        ('disconnected', 'Disconnected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whatsapp_accounts')
    phone_number = models.CharField(max_length=20, unique=True)
    whatsapp_id = models.CharField(max_length=255, unique=True)
    access_token = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='connected')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} ({self.status})"

class InstagramReel(models.Model):
    """Model for Instagram reels"""
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='reels')
    reel_id = models.CharField(max_length=255, unique=True)
    title = models.TextField(null=True, blank=True)
    thumbnail_url = models.TextField(null=True, blank=True)
    permalink = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reel: {self.title or self.reel_id}"

class CommentLog(models.Model):
    """Log of comments on reels for demo and real tracking"""
    reel = models.ForeignKey(InstagramReel, on_delete=models.CASCADE, related_name='comments')
    comment_id = models.CharField(max_length=255, unique=True)
    commenter_username = models.CharField(max_length=255)
    comment_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Comment by {self.commenter_username}: {self.comment_text[:50]}"

class DMLog(models.Model):
    """Log of DMs sent for tracking"""
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='dm_logs')
    recipient_username = models.CharField(max_length=255)
    message_text = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"DM to {self.recipient_username}: {self.message_text[:50]}"


class InstagramSession(models.Model):
    account = models.OneToOneField(
        'InstagramAccount', 
        on_delete=models.CASCADE, 
        related_name='session_data_obj'
    )
    session_json = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session for {self.account.username}"

class InstagramComment(models.Model):
    """Model for generic Instagram comments for robust polling and de-duplication"""
    account = models.ForeignKey(InstagramAccount, on_delete=models.CASCADE, related_name='all_comments')
    comment_id = models.CharField(max_length=255, unique=True)
    media_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    text = models.TextField()
    timestamp = models.DateTimeField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment {self.comment_id} on {self.media_id} by {self.username}"


# ── Supplementary models — imported here so Django ORM discovers them ─────────
# These are defined in separate files for organisation but must be registered
# in the same app for makemigrations to include them.
from .action_models import ActionExecution  # noqa: F401, E402
from .event_models import WorkflowEvent, WorkflowExecution  # noqa: F401, E402
