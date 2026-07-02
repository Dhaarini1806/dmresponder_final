from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import UserSettings, SMTPSettings, APIKey, TeamMember
from .serializers import UserSettingsSerializer, SMTPSettingsSerializer, APIKeySerializer, TeamMemberSerializer

class UserSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for user settings"""
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSettings.objects.filter(user=self.request.user)

class SMTPSettingsViewSet(viewsets.ModelViewSet):
    """ViewSet for SMTP settings"""
    serializer_class = SMTPSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SMTPSettings.objects.filter(user=self.request.user)

class APIKeyViewSet(viewsets.ModelViewSet):
    """ViewSet for API keys"""
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return APIKey.objects.filter(user=self.request.user)

class TeamMemberViewSet(viewsets.ModelViewSet):
    """ViewSet for team members"""
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TeamMember.objects.filter(organization=self.request.user)
