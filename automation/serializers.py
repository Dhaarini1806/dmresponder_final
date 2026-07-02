from rest_framework import serializers
from .models import AutomationWorkflow, WorkflowNode, WorkflowConnection, AutomationExecution

class WorkflowNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowNode
        fields = '__all__'

class WorkflowConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowConnection
        fields = '__all__'

class AutomationWorkflowSerializer(serializers.ModelSerializer):
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    connections = WorkflowConnectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = AutomationWorkflow
        fields = '__all__'
        read_only_fields = ('user',)

class AutomationExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationExecution
        fields = '__all__'
