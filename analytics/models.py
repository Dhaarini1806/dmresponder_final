from django.db import models
from django.contrib.auth.models import User

class AnalyticsEvent(models.Model):
    """Track analytics events"""
    EVENT_TYPES = [
        ('lead_created', 'Lead Created'),
        ('message_sent', 'Message Sent'),
        ('automation_triggered', 'Automation Triggered'),
        ('conversion', 'Conversion'),
        ('page_view', 'Page View'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analytics_events')
    event_type = models.CharField(max_length=100, choices=EVENT_TYPES)
    platform = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class DailyMetrics(models.Model):
    """Aggregated daily metrics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_metrics')
    date = models.DateField()
    total_leads = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)
    active_automations = models.IntegerField(default=0)
    broadcast_success_rate = models.FloatField(default=0.0)
    platform_distribution = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class Notification(models.Model):
    """System notifications"""
    TYPE_CHOICES = [
        ('broadcast_complete', 'Broadcast Complete'),
        ('lead_created', 'Lead Created'),
        ('workflow_failed', 'Workflow Failed'),
        ('account_disconnected', 'Account Disconnected'),
        ('system_error', 'System Error'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
