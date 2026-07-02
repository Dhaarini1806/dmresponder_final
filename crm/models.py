from django.db import models
from django.contrib.auth.models import User

class LeadPipeline(models.Model):
    """Pipeline for leads"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pipelines')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class LeadStage(models.Model):
    """Stages within a pipeline"""
    pipeline = models.ForeignKey(LeadPipeline, on_delete=models.CASCADE, related_name='stages')
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"

class Lead(models.Model):
    """Lead model for CRM"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    
    SOURCE_CHOICES = [
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('whatsapp', 'WhatsApp'),
        ('website', 'Website'),
        ('meta_ads', 'Meta Ads'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leads')
    stage = models.ForeignKey(LeadStage, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='new')
    lead_score = models.IntegerField(default=0)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

class LeadNote(models.Model):
    """Notes for a lead"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class LeadTag(models.Model):
    """Tags for a lead"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=100)

class LeadTimeline(models.Model):
    """Timeline of events for a lead"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='timeline')
    event_type = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
