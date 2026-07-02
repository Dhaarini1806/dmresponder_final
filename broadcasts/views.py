from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Broadcast, BroadcastRecipient, ScheduledPost
from .serializers import BroadcastSerializer, BroadcastRecipientSerializer, ScheduledPostSerializer

class BroadcastViewSet(viewsets.ModelViewSet):
    """ViewSet for broadcasts"""
    serializer_class = BroadcastSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Broadcast.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        broadcast = self.get_object()
        # In a real app, this would trigger a Celery task
        broadcast.status = 'sending'
        broadcast.save()
        return Response({'status': 'sending'})

class BroadcastRecipientViewSet(viewsets.ModelViewSet):
    """ViewSet for broadcast recipients"""
    serializer_class = BroadcastRecipientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BroadcastRecipient.objects.filter(broadcast__user=self.request.user)

class ScheduledPostViewSet(viewsets.ModelViewSet):
    """ViewSet for scheduled posts"""
    serializer_class = ScheduledPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ScheduledPost.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
