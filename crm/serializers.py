from rest_framework import serializers
from .models import Lead, LeadPipeline, LeadStage, LeadNote, LeadTag, LeadTimeline

class LeadStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadStage
        fields = '__all__'

class LeadPipelineSerializer(serializers.ModelSerializer):
    stages = LeadStageSerializer(many=True, read_only=True)
    
    class Meta:
        model = LeadPipeline
        fields = '__all__'

class LeadNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadNote
        fields = '__all__'

class LeadTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTag
        fields = '__all__'

class LeadTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadTimeline
        fields = '__all__'

class LeadSerializer(serializers.ModelSerializer):
    notes = LeadNoteSerializer(many=True, read_only=True)
    tags = LeadTagSerializer(many=True, read_only=True)
    timeline = LeadTimelineSerializer(many=True, read_only=True)
    
    class Meta:
        model = Lead
        fields = '__all__'
        read_only_fields = ('user',)
