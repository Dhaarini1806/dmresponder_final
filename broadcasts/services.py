from .models import Broadcast, BroadcastRecipient, ScheduledPost
from django.utils import timezone
from instagram.models import DMLog, InstagramAccount

class BroadcastService:
    @staticmethod
    def send_broadcast(broadcast_id):
        broadcast = Broadcast.objects.get(id=broadcast_id)
        broadcast.status = 'sending'
        broadcast.save()
        
        recipients = broadcast.recipients.filter(status='pending')
        for recipient in recipients:
            try:
                # In a real app, this would call the platform API
                # For now, we simulate sending
                if broadcast.platform == 'instagram':
                    # Find a connected account to send from
                    account = InstagramAccount.objects.filter(user=broadcast.user, status='connected').first()
                    if account:
                        DMLog.objects.create(
                            account=account,
                            recipient_username=recipient.recipient_username,
                            message_text=broadcast.message_text,
                            status='sent'
                        )
                
                recipient.status = 'sent'
                recipient.sent_at = timezone.now()
                recipient.save()
                broadcast.sent_count += 1
            except Exception as e:
                recipient.status = 'failed'
                recipient.error_message = str(e)
                recipient.save()
                broadcast.failed_count += 1
        
        broadcast.status = 'sent'
        broadcast.save()
        return broadcast
