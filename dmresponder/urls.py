from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from core.views import (
    landing_page, privacy_policy, terms_of_service, data_deletion,
    login_view, signup_view, logout_view, ContactFormViewSet
)
from core.dashboard_views import (
    dashboard, connected_accounts, automation_reels, inbox,
    crm_leads, analytics, broadcasts, settings, content_calendar,
    link_post, engagement_starter, stories, default_settings
)
from instagram.views import (
    InstagramAccountViewSet, FacebookPageViewSet, WhatsAppAccountViewSet,
    InstagramReelViewSet, CommentLogViewSet, DMLogViewSet
)
from automation.views import (
    AutomationWorkflowViewSet, WorkflowNodeViewSet,
    WorkflowConnectionViewSet, AutomationExecutionViewSet
)
from crm.views import (
    LeadViewSet, LeadPipelineViewSet, LeadStageViewSet
)
from inbox.views import (
    ConversationViewSet, MessageViewSet, QuickReplyViewSet
)
from broadcasts.views import (
    BroadcastViewSet, BroadcastRecipientViewSet, ScheduledPostViewSet
)
from analytics.views import (
    AnalyticsEventViewSet, DailyMetricsViewSet, NotificationViewSet
)
from settings.views import (
    UserSettingsViewSet, SMTPSettingsViewSet, APIKeyViewSet, TeamMemberViewSet
)
from dmresponder.views import health_check

# Create router and register viewsets
router = DefaultRouter()
router.register(r'contact-form', ContactFormViewSet, basename='contact-form')
router.register(r'instagram/accounts', InstagramAccountViewSet, basename='instagram-account')
router.register(r'facebook/pages', FacebookPageViewSet, basename='facebook-page')
router.register(r'whatsapp/accounts', WhatsAppAccountViewSet, basename='whatsapp-account')
router.register(r'instagram/reels', InstagramReelViewSet, basename='instagram-reel')
router.register(r'instagram/comments', CommentLogViewSet, basename='instagram-comment')
router.register(r'instagram/dms', DMLogViewSet, basename='instagram-dm')
router.register(r'automation/workflows', AutomationWorkflowViewSet, basename='automation-workflow')
router.register(r'automation/nodes', WorkflowNodeViewSet, basename='workflow-node')
router.register(r'automation/connections', WorkflowConnectionViewSet, basename='workflow-connection')
router.register(r'automation/executions', AutomationExecutionViewSet, basename='automation-execution')
router.register(r'crm/leads', LeadViewSet, basename='lead')
router.register(r'crm/pipelines', LeadPipelineViewSet, basename='lead-pipeline')
router.register(r'crm/stages', LeadStageViewSet, basename='lead-stage')
router.register(r'inbox/conversations', ConversationViewSet, basename='conversation')
router.register(r'inbox/messages', MessageViewSet, basename='message')
router.register(r'inbox/quick-replies', QuickReplyViewSet, basename='quick-reply')
router.register(r'broadcasts/campaigns', BroadcastViewSet, basename='broadcast')
router.register(r'broadcasts/recipients', BroadcastRecipientViewSet, basename='broadcast-recipient')
router.register(r'broadcasts/scheduled-posts', ScheduledPostViewSet, basename='scheduled-post')
router.register(r'analytics/events', AnalyticsEventViewSet, basename='analytics-event')
router.register(r'analytics/daily-metrics', DailyMetricsViewSet, basename='daily-metric')
router.register(r'analytics/notifications', NotificationViewSet, basename='notification')
router.register(r'settings/user', UserSettingsViewSet, basename='user-settings')
router.register(r'settings/smtp', SMTPSettingsViewSet, basename='smtp-settings')
router.register(r'settings/api-keys', APIKeyViewSet, basename='api-key')
router.register(r'settings/team', TeamMemberViewSet, basename='team-member')

urlpatterns = [
    # Pages
    path('', landing_page, name='landing_page'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('terms-of-service/', terms_of_service, name='terms_of_service'),
    path('data-deletion/', data_deletion, name='data_deletion'),

    # Dashboard Pages
    path('dashboard/', dashboard, name='dashboard'),
    path('instagram/connected-accounts/', connected_accounts, name='connected_accounts'),
    path('automation/reels/', automation_reels, name='automation_reels'),
    path('automation/stories/', stories, name='stories'),
    path('automation/default-settings/', default_settings, name='default_settings'),
    path('automation/link-post/<int:reel_id>/', link_post, name='link_post'),
    path('automation/engagement-starter/', engagement_starter, name='engagement_starter'),
    path('inbox/', inbox, name='inbox'),
    path('crm/leads/', crm_leads, name='crm_leads'),
    path('analytics/', analytics, name='analytics'),
    path('broadcasts/', broadcasts, name='broadcasts'),
    path('settings/', settings, name='settings'),
    path('calendar/', content_calendar, name='content_calendar'),

    # Admin
    path('admin/', admin.site.urls),
    
    # Auth
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('accounts/', include('allauth.urls')),
    
    # API
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path('api/health/', health_check, name='health'),
]
