from rest_framework import serializers
from .models import Broadcast, BroadcastRecipient, ScheduledPost

class BroadcastRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = BroadcastRecipient
        fields = '__all__'

class BroadcastSerializer(serializers.ModelSerializer):
    recipients = BroadcastRecipientSerializer(many=True, read_only=True)
    
    class Meta:
        model = Broadcast
        fields = '__all__'
        read_only_fields = ('user',)

class ScheduledPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledPost
        fields = '__all__'
        read_only_fields = ('user',)
