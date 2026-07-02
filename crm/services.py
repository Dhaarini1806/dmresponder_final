from .models import Lead, LeadTimeline, LeadStage, LeadPipeline
from django.utils import timezone

class CRMService:
    @staticmethod
    def create_lead(user, name, email=None, phone=None, source='manual', status='new'):
        lead = Lead.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            source=source,
            status=status
        )
        LeadTimeline.objects.create(
            lead=lead,
            event_type='lead_created',
            description=f"Lead created from {source}"
        )
        return lead

    @staticmethod
    def update_lead_stage(lead, stage_id):
        stage = LeadStage.objects.get(id=stage_id)
        old_stage = lead.stage.name if lead.stage else "None"
        lead.stage = stage
        lead.save()
        LeadTimeline.objects.create(
            lead=lead,
            event_type='stage_changed',
            description=f"Stage changed from {old_stage} to {stage.name}"
        )
        return lead
