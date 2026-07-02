from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message, QuickReply
from .serializers import ConversationSerializer, MessageSerializer, QuickReplySerializer

class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for conversations"""
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        message_text = request.data.get('message_text')
        message = Message.objects.create(
            conversation=conversation,
            sender_type='user',
            message_text=message_text
        )
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for individual messages"""
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(conversation__user=self.request.user)

class QuickReplyViewSet(viewsets.ModelViewSet):
    """ViewSet for quick replies"""
    serializer_class = QuickReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return QuickReply.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
