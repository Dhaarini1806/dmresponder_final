from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AnalyticsEvent, DailyMetrics, Notification
from .serializers import AnalyticsEventSerializer, DailyMetricsSerializer, NotificationSerializer

class AnalyticsEventViewSet(viewsets.ModelViewSet):
    """ViewSet for analytics events"""
    serializer_class = AnalyticsEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AnalyticsEvent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        from inbox.models import Conversation
        from crm.models import Lead
        from automation.models import AutomationExecution
        from instagram.action_models import ActionExecution
        from django.db import models

        user = request.user
        
        # Total Conversations
        conv_count = Conversation.objects.filter(user=user).count()
        
        # Total Leads
        lead_count = Lead.objects.filter(user=user).count()
        
        # DM Replies Sent (Successful outbound actions)
        replies_count = ActionExecution.objects.filter(
            instagram_account__user=user,
            status='success',
            action_type__in=['SEND_DM', 'REPLY_DM']
        ).count()
        
        # Conversion Rate (Leads / Conversations)
        conv_rate = (lead_count / conv_count * 100) if conv_count > 0 else 0
        
        # Executions Count
        execution_count = AutomationExecution.objects.filter(workflow__user=user).count()
        
        # Top Automations
        top_automations = AutomationExecution.objects.filter(workflow__user=user)\
            .values('workflow__name', 'workflow__trigger_type')\
            .annotate(count=models.Count('id'))\
            .order_by('-count')[:5]
            
        # Recent Activity (Latest Leads)
        recent_leads = Lead.objects.filter(user=user).order_by('-created_at')[:5]
        
        recent_activity = []
        for lead in recent_leads:
            recent_activity.append({
                'initials': ''.join([n[0] for n in lead.name.split() if n])[:2].upper() or 'U',
                'name': lead.name,
                'source': lead.source,
                'time': lead.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return Response({
            'conversations': conv_count,
            'leads': lead_count,
            'dm_replies': replies_count,
            'conversion_rate': round(conv_rate, 1),
            'total_executions': execution_count,
            'revenue': 0,
            'top_automations': list(top_automations),
            'recent_activity': recent_activity
        })
class DailyMetricsViewSet(viewsets.ModelViewSet):
    """ViewSet for daily metrics"""
    serializer_class = DailyMetricsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DailyMetrics.objects.filter(user=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'read'})
