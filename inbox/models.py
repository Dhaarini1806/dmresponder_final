from django.db import models
from django.contrib.auth.models import User

class Conversation(models.Model):
    """Conversation model for inbox"""
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    instagram_account = models.ForeignKey('instagram.InstagramAccount', on_delete=models.CASCADE, null=True, blank=True, related_name='conversations')
    conversation_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    participant_id = models.CharField(max_length=255)
    participant_username = models.CharField(max_length=255)
    participants = models.JSONField(default=list, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    last_message = models.TextField(null=True, blank=True)
    last_message_at = models.DateTimeField(auto_now=True)
    last_message_timestamp = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_message_at']

    def __str__(self):
        return f"{self.platform} - {self.participant_username}"

class Message(models.Model):
    """Individual messages within a conversation"""
    SENDER_TYPE_CHOICES = [
        ('user', 'User'),
        ('participant', 'Participant'),
        ('bot', 'Bot'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPE_CHOICES)
    sender_id = models.CharField(max_length=255, null=True, blank=True)
    sender_username = models.CharField(max_length=255, null=True, blank=True)
    message_text = models.TextField()
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    message_type = models.CharField(max_length=50, default='text')
    timestamp = models.DateTimeField(null=True, blank=True)
    processed = models.BooleanField(default=False)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender_type}: {self.message_text[:50]}"

class QuickReply(models.Model):
    """Quick reply templates"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_replies')
    shortcut = models.CharField(max_length=50)
    message_text = models.TextField()

    def __str__(self):
        return self.shortcut
