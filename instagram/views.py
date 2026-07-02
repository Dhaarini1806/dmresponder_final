from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import InstagramAccount, FacebookPage, WhatsAppAccount, InstagramReel, CommentLog, DMLog
from .serializers import (
    InstagramAccountSerializer, FacebookPageSerializer, WhatsAppAccountSerializer,
    InstagramReelSerializer, CommentLogSerializer, DMLogSerializer
)
from .services import InstagramService

class InstagramAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for Instagram accounts"""
    serializer_class = InstagramAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InstagramAccount.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='create_demo_account')
    def connect_demo(self, request):
        """Connect a demo account"""
        account = InstagramService.create_demo_account(request.user)
        serializer = self.get_serializer(account)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='connect_real')
    def connect_real(self, request):
        """Connect a real Instagram account"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # First create the account record
            account_id = f"ig_{username}"
            account, created = InstagramAccount.objects.get_or_create(
                account_id=account_id,
                defaults={
                    "user": request.user,
                    "username": username,
                    "status": "pending",
                    "is_demo": False,
                    "automation_status": True,
                },
            )
            
            # Then attempt login
            InstagramService.login_instagram_account(account, username, password)
            
            serializer = self.get_serializer(account)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            # If login fails and we just created it, we could delete it, but status is disconnected
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to connect real account: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def reels(self, request, pk=None):
        """Get reels for an account and trigger a sync beforehand"""
        account = self.get_object()
        try:
            # Dynamically sync reels from Instagram before listing them
            InstagramService.sync_reels(account)
        except Exception as e:
            # Log error but return existing database reels so application remains functional
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error syncing reels for account {account.username}: {e}")
            
        reels = account.reels.all()
        serializer = InstagramReelSerializer(reels, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='sync_reels')
    def sync_reels_endpoint(self, request, pk=None):
        """Manually trigger a sync of reels for the account"""
        account = self.get_object()
        try:
            InstagramService.sync_reels(account)
            return Response({'status': 'synced'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FacebookPageViewSet(viewsets.ModelViewSet):
    """ViewSet for Facebook Pages"""
    serializer_class = FacebookPageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FacebookPage.objects.filter(user=self.request.user)

class WhatsAppAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for WhatsApp accounts"""
    serializer_class = WhatsAppAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WhatsAppAccount.objects.filter(user=self.request.user)

class InstagramReelViewSet(viewsets.ModelViewSet):
    """ViewSet for Instagram reels"""
    serializer_class = InstagramReelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return InstagramReel.objects.filter(account__user=self.request.user)

class CommentLogViewSet(viewsets.ModelViewSet):
    """ViewSet for comment logs"""
    serializer_class = CommentLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CommentLog.objects.filter(reel__account__user=self.request.user)

    @action(detail=False, methods=['post'], url_path='simulate_comment')
    def simulate_comment(self, request):
        """Simulate a comment trigger event for testing workflows"""
        reel_id = request.data.get('reel_id')
        comment_text = request.data.get('comment_text', '')
        commenter_username = request.data.get('commenter_username', 'test_user')

        if not reel_id:
            return Response({'error': 'reel_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reel = InstagramReel.objects.get(pk=reel_id, account__user=request.user)
        except InstagramReel.DoesNotExist:
            return Response({'error': 'Reel not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create simulated comment log
        import uuid
        comment_id = f"sim_{uuid.uuid4().hex[:12]}"
        comment_log = CommentLog.objects.create(
            reel=reel,
            comment_id=comment_id,
            commenter_username=commenter_username,
            comment_text=comment_text,
            processed=False
        )

        # Trigger workflow directly using our workflow processing service
        from automation.services import AutomationService
        AutomationService.process_new_comment(comment_log)

        return Response({
            'status': 'simulated',
            'comment_id': comment_id,
            'processed': comment_log.processed
        }, status=status.HTTP_201_CREATED)


class DMLogViewSet(viewsets.ModelViewSet):
    """ViewSet for DM logs"""
    serializer_class = DMLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DMLog.objects.filter(account__user=self.request.user)
