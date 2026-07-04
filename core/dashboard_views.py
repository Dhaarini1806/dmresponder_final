from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    """Main dashboard view"""
    return render(request, 'dashboard.html')

@login_required
def connected_accounts(request):
    """Connected accounts management page"""
    return render(request, 'connected_accounts.html')

@login_required
def automation_reels(request):
    """Reel automation builder page"""
    return render(request, 'automation_reels.html')

@login_required
def link_post(request, reel_id):
    """Link Post UI page for configuring automation"""
    return render(request, 'link_post.html', {'reel_id': reel_id})

@login_required
def engagement_starter(request):
    """Engagement Starter global config page"""
    return render(request, 'engagement_starter.html')

@login_required
def inbox(request):
    """Inbox/Conversations page"""
    return render(request, 'inbox.html')

@login_required
def crm_leads(request):
    """CRM leads management page"""
    return render(request, 'crm_leads.html')

@login_required
def analytics(request):
    """Analytics dashboard"""
    return render(request, 'analytics.html')

@login_required
def broadcasts(request):
    """Broadcasts management page"""
    return render(request, 'broadcasts.html')

@login_required
def settings(request):
    """Settings page"""
    return render(request, 'settings.html')

@login_required
def content_calendar(request):
    """Content calendar and scheduling"""
    return render(request, 'content_calendar.html')

@login_required
def stories(request):
    """Stories feature page"""
    return render(request, 'stories.html')

@login_required
def default_settings(request):
    """Default Settings page with Media Template builder"""
    return render(request, 'default_settings.html')

@login_required
def pricing_plans(request):
    """Pricing Plans page"""
    return render(request, 'pricing_plans.html')
