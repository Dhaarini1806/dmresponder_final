from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AutomationWorkflow, WorkflowNode, WorkflowConnection, AutomationExecution
from .serializers import (
    AutomationWorkflowSerializer, WorkflowNodeSerializer,
    WorkflowConnectionSerializer, AutomationExecutionSerializer
)
from .services import AutomationService

class AutomationWorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for automation workflows"""
    serializer_class = AutomationWorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AutomationWorkflow.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Manually execute a workflow"""
        workflow = self.get_object()
        trigger_data = request.data.get('trigger_data', {})
        execution = AutomationService.execute_workflow(workflow, trigger_data)
        serializer = AutomationExecutionSerializer(execution)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='nodes_bulk')
    def nodes_bulk(self, request, pk=None):
        """Bulk save nodes and connections for a workflow"""
        workflow = self.get_object()
        nodes_data = request.data.get('nodes', [])
        connections_data = request.data.get('connections', [])

        # Delete existing nodes and connections
        workflow.nodes.all().delete()
        workflow.connections.all().delete()

        # Recreate nodes
        created_nodes = {}
        for node_data in nodes_data:
            node = WorkflowNode.objects.create(
                workflow=workflow,
                node_id=node_data.get('node_id'),
                node_type=node_data.get('node_type'),
                config=node_data.get('config', {}),
                position_x=node_data.get('position_x', 0),
                position_y=node_data.get('position_y', 0)
            )
            created_nodes[node.node_id] = node

        # Recreate connections
        for conn_data in connections_data:
            source_id = conn_data.get('source_node')
            target_id = conn_data.get('target_node')
            
            if source_id in created_nodes and target_id in created_nodes:
                WorkflowConnection.objects.create(
                    workflow=workflow,
                    source_node=created_nodes[source_id],
                    target_node=created_nodes[target_id],
                    source_handle=conn_data.get('source_handle'),
                    target_handle=conn_data.get('target_handle')
                )

        return Response({'status': 'success', 'nodes_count': len(nodes_data), 'connections_count': len(connections_data)})

class WorkflowNodeViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow nodes"""
    serializer_class = WorkflowNodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkflowNode.objects.filter(workflow__user=self.request.user)

class WorkflowConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow connections"""
    serializer_class = WorkflowConnectionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkflowConnection.objects.filter(workflow__user=self.request.user)

class AutomationExecutionViewSet(viewsets.ModelViewSet):
    """ViewSet for automation executions"""
    serializer_class = AutomationExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AutomationExecution.objects.filter(workflow__user=self.request.user)
