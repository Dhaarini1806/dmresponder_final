from django.db import models
from django.contrib.auth.models import User

class Broadcast(models.Model):
    """Broadcast campaign model"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    SEND_TYPE_CHOICES = [
        ('immediate', 'Immediate'),
        ('scheduled', 'Scheduled'),
        ('recurring', 'Recurring'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broadcasts')
    title = models.CharField(max_length=255)
    message_text = models.TextField()
    platform = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    send_type = models.CharField(max_length=20, choices=SEND_TYPE_CHOICES, default='immediate')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    recurring_config = models.JSONField(null=True, blank=True)
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

class BroadcastRecipient(models.Model):
    """Track broadcast recipients"""
    broadcast = models.ForeignKey(Broadcast, on_delete=models.CASCADE, related_name='recipients')
    recipient_id = models.CharField(max_length=255)
    recipient_username = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], default='pending')
    error_message = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.broadcast.title} -> {self.recipient_username}"

class ScheduledPost(models.Model):
    """Model for scheduled social media posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_posts')
    platform = models.CharField(max_length=50)
    media_url = models.URLField()
    caption = models.TextField()
    hashtags = models.TextField(null=True, blank=True)
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('posted', 'Posted'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.platform} Post - {self.scheduled_at}"
