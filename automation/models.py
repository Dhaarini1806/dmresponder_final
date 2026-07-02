from django.db import models
from django.contrib.auth.models import User
from instagram.models import InstagramReel

class AutomationWorkflow(models.Model):
    """Main automation workflow model"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('draft', 'Draft'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='automation_workflows')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    # Optional link to a specific Instagram reel for per‑reel workflows
    reel = models.ForeignKey('instagram.InstagramReel', null=True, blank=True, on_delete=models.CASCADE, related_name='workflows')
    trigger_type = models.CharField(max_length=50)
    trigger_config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WorkflowNode(models.Model):
    """Nodes within a workflow"""
    NODE_TYPES = [
        ('trigger', 'Trigger'),
        ('condition', 'Condition'),
        ('delay', 'Delay'),
        ('send_dm', 'Send DM'),
        ('collect_info', 'Collect Info'),
        ('save_lead', 'Save Lead'),
        ('send_whatsapp', 'Send WhatsApp'),
        ('notify_admin', 'Notify Admin'),
        ('branch', 'Branch'),
        ('wait', 'Wait'),
    ]
    
    workflow = models.ForeignKey(AutomationWorkflow, on_delete=models.CASCADE, related_name='nodes')
    node_id = models.CharField(max_length=100)
    node_type = models.CharField(max_length=50, choices=NODE_TYPES)
    config = models.JSONField(default=dict)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)

    def __str__(self):
        return f"{self.workflow.name} - {self.node_type} ({self.node_id})"

class WorkflowConnection(models.Model):
    """Connections between nodes"""
    workflow = models.ForeignKey(AutomationWorkflow, on_delete=models.CASCADE, related_name='connections')
    source_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name='source_connections')
    target_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name='target_connections')
    source_handle = models.CharField(max_length=100, null=True, blank=True)
    target_handle = models.CharField(max_length=100, null=True, blank=True)

class AutomationExecution(models.Model):
    """Log of automation executions"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('in_progress', 'In Progress'),
    ]
    
    workflow = models.ForeignKey(AutomationWorkflow, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    execution_data = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Execution {self.id}: {self.status}"
