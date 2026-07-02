from django.http import JsonResponse
from automation.models import AutomationWorkflow, WorkflowNode
from crm.models import Lead

def health_check(request):
    try:
        # verify DB connections
        counts = {
            'workflows': AutomationWorkflow.objects.count(),
            'nodes': WorkflowNode.objects.count(),
            'leads': Lead.objects.count()
        }
        return JsonResponse({'db': 'ok', 'counts': counts})
    except Exception as e:
        return JsonResponse({'db': 'error', 'error': str(e)}, status=500)
