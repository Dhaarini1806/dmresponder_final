from rest_framework import serializers
from .models import InstagramAccount, FacebookPage, WhatsAppAccount, InstagramReel, CommentLog, DMLog

class InstagramAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramAccount
        fields = '__all__'

class FacebookPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacebookPage
        fields = '__all__'

class WhatsAppAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppAccount
        fields = '__all__'

class InstagramReelSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstagramReel
        fields = '__all__'

class CommentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentLog
        fields = '__all__'

class DMLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DMLog
        fields = '__all__'
