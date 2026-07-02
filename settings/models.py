from django.db import models
from django.contrib.auth.models import User

class UserSettings(models.Model):
    """User account settings"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dmresponder_settings')
    company_name = models.CharField(max_length=255, null=True, blank=True)
    company_logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    timezone = models.CharField(max_length=100, default='UTC')
    language = models.CharField(max_length=10, default='en')
    branding_config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings for {self.user.username}"

class SMTPSettings(models.Model):
    """Email SMTP configuration"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='smtp_settings')
    smtp_host = models.CharField(max_length=255)
    smtp_port = models.IntegerField()
    smtp_user = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=255)
    from_email = models.EmailField()
    use_tls = models.BooleanField(default=True)
    is_active = models.BooleanField(default=False)

class APIKey(models.Model):
    """API keys for external integrations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=255)
    service = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

class TeamMember(models.Model):
    """Team member management"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('agent', 'Agent'),
    ]
    
    organization = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_assignments')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    permissions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
