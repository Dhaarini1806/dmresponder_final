from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Lead, LeadPipeline, LeadStage, LeadNote, LeadTag, LeadTimeline
from .serializers import (
    LeadSerializer, LeadPipelineSerializer, LeadStageSerializer,
    LeadNoteSerializer, LeadTagSerializer, LeadTimelineSerializer
)

class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet for leads"""
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Lead.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        lead = self.get_object()
        serializer = LeadNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lead=lead, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LeadPipelineViewSet(viewsets.ModelViewSet):
    """ViewSet for lead pipelines"""
    serializer_class = LeadPipelineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeadPipeline.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class LeadStageViewSet(viewsets.ModelViewSet):
    """ViewSet for lead stages"""
    serializer_class = LeadStageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeadStage.objects.filter(pipeline__user=self.request.user)
