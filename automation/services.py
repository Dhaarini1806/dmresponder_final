from django.utils import timezone
from .models import AutomationWorkflow, AutomationExecution, WorkflowNode, WorkflowConnection
from instagram.models import CommentLog, DMLog, InstagramAccount, WhatsAppAccount
from crm.models import Lead, LeadTimeline
import json
import time
import requests

class AutomationService:
    """Service layer for automation workflow execution"""
    
    @staticmethod
    def execute_workflow(workflow, trigger_data=None):
        """Execute a workflow based on a trigger"""
        execution = AutomationExecution.objects.create(
            workflow=workflow,
            status='in_progress',
            execution_data={'trigger_data': trigger_data}
        )
        
        try:
            # Find the trigger node
            trigger_node = workflow.nodes.filter(node_type='trigger').first()
            if not trigger_node:
                raise Exception("No trigger node found in workflow")
            
            context = {
                'trigger_data': trigger_data,
                'variables': {},
                'execution_id': execution.id,
                'user_id': workflow.user_id  # store ID only — User object is not JSON-serializable
            }
            
            # Start execution from the trigger node
            AutomationService._execute_next_nodes(trigger_node, context)
                
            execution.status = 'success'
            execution.completed_at = timezone.now()
            # Only persist JSON-serializable scalars
            execution.execution_data['result'] = {
                'variables': context.get('variables', {})
            }
            execution.save()
            
        except Exception as e:
            execution.status = 'failed'
            execution.execution_data['error'] = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            
        return execution

    @staticmethod
    def _execute_next_nodes(current_node, context):
        """Recursively execute next nodes in the workflow"""
        connections = WorkflowConnection.objects.filter(source_node=current_node)
        
        for conn in connections:
            next_node = conn.target_node
            result = AutomationService._execute_node(next_node, context)
            
            # Update context with node results
            if result:
                context['variables'][f"node_{next_node.node_id}"] = result
            
            # Continue execution
            AutomationService._execute_next_nodes(next_node, context)

    @staticmethod
    def _execute_node(node, context):
        """Execute a single workflow node"""
        node_type = node.node_type
        config = node.config or {}
        user_id = context.get('user_id')
        from django.contrib.auth.models import User as DjangoUser
        try:
            user = DjangoUser.objects.get(pk=user_id) if user_id else None
        except DjangoUser.DoesNotExist:
            user = None

        if node_type == 'send_dm':
            message = config.get('message', '')
            account_pk = context.get('trigger_data', {}).get('account_pk')
            sender_id = context.get('trigger_data', {}).get('sender_id')
            recipient_username = context.get('trigger_data', {}).get('username')
            
            if account_pk and (sender_id or recipient_username):
                from instagram.models import InstagramAccount
                from instagram.action_executor import ActionExecutor
                try:
                    account = InstagramAccount.objects.get(pk=account_pk)
                    payload = {'account_id': account.pk, 'text': message}
                    if sender_id:
                        payload['recipient_id'] = sender_id
                    if recipient_username:
                        payload['recipient_username'] = recipient_username
                        
                    ActionExecutor().submit('SEND_DM', payload, None)
                    return {'status': 'queued', 'platform': 'instagram', 'message': message}
                except InstagramAccount.DoesNotExist:
                    pass
            return {'status': 'failed', 'error': 'Missing account or recipient'}
            
        elif node_type == 'send_whatsapp':
            message = config.get('message', '')
            phone = config.get('phone', context.get('trigger_data', {}).get('phone', ''))
            # Future integration point for WhatsApp API
            return {'status': 'queued', 'platform': 'whatsapp', 'message': message, 'to': phone}
            
        elif node_type == 'save_lead':
            lead_data = {
                'user': user,
                'name': context.get('trigger_data', {}).get('username', 'Unknown'),
                'source': context.get('trigger_data', {}).get('platform', 'instagram'),
                'status': 'new'
            }
            lead = Lead.objects.create(**lead_data)
            LeadTimeline.objects.create(
                lead=lead,
                event_type='automation_created',
                description=f"Lead created via automation workflow: {node.workflow.name}"
            )
            return {'status': 'created', 'lead_id': lead.id}
            
        elif node_type == 'delay':
            seconds = config.get('seconds', 0)
            # In a real app, this would be a task delay
            return {'status': 'delayed', 'seconds': seconds}
            
        return {}

    @staticmethod
    def process_new_comment(comment):
        """Check if a comment matches any automations and execute them"""
        reel = comment.reel
        workflows = AutomationWorkflow.objects.filter(
            user=reel.account.user,
            status='active',
            trigger_type='comment'
        )
        
        for workflow in workflows:
            trigger_config = workflow.trigger_config or {}
            keyword = trigger_config.get('keyword', '').lower()
            
            if keyword == '' or keyword in comment.comment_text.lower():
                AutomationService.execute_workflow(workflow, {
                    'platform': 'instagram',
                    'comment_id': comment.comment_id,
                    'comment_text': comment.comment_text,
                    'username': comment.commenter_username,
                    'reel_id': reel.reel_id,
                    'account_pk': reel.account.pk,
                    'sender_id': comment.commenter_username
                })
                comment.processed = True
                comment.save()

    @staticmethod
    def process_whatsapp_message(whatsapp_account, message_data):
        """Handle incoming WhatsApp messages"""
        workflows = AutomationWorkflow.objects.filter(
            user=whatsapp_account.user,
            status='active',
            trigger_type='whatsapp'
        )
        
        for workflow in workflows:
            trigger_config = workflow.trigger_config or {}
            keyword = trigger_config.get('keyword', '').lower()
            text = message_data.get('text', '').lower()
            
            if keyword == '' or keyword in text:
                AutomationService.execute_workflow(workflow, {
                    'platform': 'whatsapp',
                    'phone': message_data.get('from'),
                    'text': text,
                    'whatsapp_id': message_data.get('id')
                })
