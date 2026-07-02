# DMResponder API Documentation

## Base URL
```
http://localhost:8000/api/
```

## Authentication
All endpoints require JWT authentication except for contact form and landing page endpoints.

### Obtain Token
```
POST /token/
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "password123"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Refresh Token
```
POST /token/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## Endpoints

### Instagram Accounts
```
GET    /instagram/accounts/              - List all accounts
POST   /instagram/accounts/              - Create account
GET    /instagram/accounts/{id}/         - Get account details
PUT    /instagram/accounts/{id}/         - Update account
DELETE /instagram/accounts/{id}/         - Delete account
POST   /instagram/accounts/connect_demo/ - Connect demo account
GET    /instagram/accounts/{id}/reels/   - Get reels for account
```

### Facebook Pages
```
GET    /facebook/pages/                  - List all pages
POST   /facebook/pages/                  - Create page
GET    /facebook/pages/{id}/             - Get page details
PUT    /facebook/pages/{id}/             - Update page
DELETE /facebook/pages/{id}/             - Delete page
```

### WhatsApp Accounts
```
GET    /whatsapp/accounts/               - List all accounts
POST   /whatsapp/accounts/               - Create account
GET    /whatsapp/accounts/{id}/          - Get account details
PUT    /whatsapp/accounts/{id}/          - Update account
DELETE /whatsapp/accounts/{id}/          - Delete account
```

### Automation Workflows
```
GET    /automation/workflows/            - List all workflows
POST   /automation/workflows/            - Create workflow
GET    /automation/workflows/{id}/       - Get workflow details
PUT    /automation/workflows/{id}/       - Update workflow
DELETE /automation/workflows/{id}/       - Delete workflow
POST   /automation/workflows/{id}/execute/ - Execute workflow
```

### Workflow Nodes
```
GET    /automation/nodes/                - List all nodes
POST   /automation/nodes/                - Create node
GET    /automation/nodes/{id}/           - Get node details
PUT    /automation/nodes/{id}/           - Update node
DELETE /automation/nodes/{id}/           - Delete node
```

### Workflow Connections
```
GET    /automation/connections/          - List all connections
POST   /automation/connections/          - Create connection
GET    /automation/connections/{id}/     - Get connection details
PUT    /automation/connections/{id}/     - Update connection
DELETE /automation/connections/{id}/     - Delete connection
```

### Leads
```
GET    /crm/leads/                       - List all leads
POST   /crm/leads/                       - Create lead
GET    /crm/leads/{id}/                  - Get lead details
PUT    /crm/leads/{id}/                  - Update lead
DELETE /crm/leads/{id}/                  - Delete lead
POST   /crm/leads/{id}/add_note/         - Add note to lead
```

### Lead Pipelines
```
GET    /crm/pipelines/                   - List all pipelines
POST   /crm/pipelines/                   - Create pipeline
GET    /crm/pipelines/{id}/              - Get pipeline details
PUT    /crm/pipelines/{id}/              - Update pipeline
DELETE /crm/pipelines/{id}/              - Delete pipeline
```

### Broadcasts
```
GET    /broadcasts/campaigns/            - List all campaigns
POST   /broadcasts/campaigns/            - Create campaign
GET    /broadcasts/campaigns/{id}/       - Get campaign details
PUT    /broadcasts/campaigns/{id}/       - Update campaign
DELETE /broadcasts/campaigns/{id}/       - Delete campaign
POST   /broadcasts/campaigns/{id}/send/  - Send campaign
```

### Conversations
```
GET    /inbox/conversations/             - List all conversations
POST   /inbox/conversations/             - Create conversation
GET    /inbox/conversations/{id}/        - Get conversation details
PUT    /inbox/conversations/{id}/        - Update conversation
DELETE /inbox/conversations/{id}/        - Delete conversation
POST   /inbox/conversations/{id}/send_message/ - Send message
```

### Analytics
```
GET    /analytics/events/                - List analytics events
POST   /analytics/events/                - Create event
GET    /analytics/daily-metrics/         - Get daily metrics
GET    /analytics/notifications/         - Get notifications
POST   /analytics/notifications/{id}/mark_as_read/ - Mark notification as read
```

### Settings
```
GET    /settings/user/                   - Get user settings
POST   /settings/user/                   - Update user settings
GET    /settings/smtp/                   - Get SMTP settings
POST   /settings/smtp/                   - Update SMTP settings
GET    /settings/api-keys/               - List API keys
POST   /settings/api-keys/               - Create API key
DELETE /settings/api-keys/{id}/          - Delete API key
GET    /settings/team/                   - List team members
POST   /settings/team/                   - Add team member
DELETE /settings/team/{id}/              - Remove team member
```

## Response Format

All responses are in JSON format:

### Success Response
```json
{
  "id": 1,
  "name": "Example",
  "created_at": "2026-06-30T12:00:00Z",
  ...
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Additional error details"
}
```

## Frontend Integration Example

```javascript
// Get JWT token
const response = await fetch('http://localhost:8000/api/token/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'user', password: 'pass' })
});
const { access } = await response.json();

// Use token in subsequent requests
const leads = await fetch('http://localhost:8000/api/crm/leads/', {
  headers: { 'Authorization': `Bearer ${access}` }
});
```

