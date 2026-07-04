# DM Responder (Instagram Automation)

DM Responder is a comprehensive Django-based application designed to automate Instagram interactions. It allows businesses to connect their Instagram professional accounts via Meta's Graph API, automatically reply to Direct Messages (DMs), moderate and respond to comments, and manage leads through an integrated CRM dashboard.

## 🚀 Features

- **Instagram Account Management**: Securely link your Instagram Business accounts via Facebook OAuth.
- **Automated Messaging**: Setup custom workflows to trigger automatic DM replies based on keywords.
- **Comment Moderation**: Automatically reply to comments on your Reels and Posts, or pull them into your inbox.
- **Centralized Inbox**: View and respond to all Instagram DMs and comments from a single unified dashboard.
- **CRM Pipeline**: Track potential leads generated from Instagram engagements through customizable pipeline stages.
- **Broadcasts**: Schedule and send bulk messages to segmented groups of leads.
- **Rich Analytics**: Track message performance, engagement rates, and lead conversion metrics.

## 🛠 Tech Stack

- **Backend**: Django 5.x, Django REST Framework
- **Database**: PostgreSQL
- **Background Tasks**: Celery & Redis (for handling Meta webhooks and scheduling broadcasts)
- **Authentication**: Django-Allauth (for Meta OAuth / Instagram Business Login)
- **Frontend**: Django Templates with Vanilla JS and TailwindCSS (or similar utility classes)

## 📦 Local Development Setup

### 1. Requirements
Ensure you have the following installed on your machine:
- Python 3.10+
- PostgreSQL
- Redis Server
- [ngrok](https://ngrok.com/) (Required for local webhook testing)

### 2. Installation
Clone the repository and install the dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory (where `manage.py` is located) and add the following keys:
```env
DEBUG=True
SECRET_KEY=your_secure_django_secret_key
DATABASE_URL=postgres://user:password@localhost:5432/dmresponder
REDIS_URL=redis://localhost:6379/0

# Meta Developer Credentials
FACEBOOK_APP_ID=your_meta_app_id
FACEBOOK_APP_SECRET=your_meta_app_secret
WEBHOOK_VERIFY_TOKEN=dmresponder_secret_token
```

### 4. Database Setup
Apply the migrations and create a superuser:
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Running the Application locally
To test the full Instagram integration locally, you need to run 3 separate processes:

**Terminal 1: Start the Django Server**
```bash
python manage.py runserver
```

**Terminal 2: Start the Celery Worker**
```bash
# On Windows, use the solo pool
celery -A dmresponder worker -l info -P solo
```

**Terminal 3: Start ngrok (for Webhooks)**
```bash
ngrok http 8000
```
*Note: Update your Meta Developer Portal with the generated ngrok URL for both your Webhook Callback and OAuth Redirect URI.*

## 🚀 Deployment

This application is configured for production deployment using **Render** (Web & Worker), **Supabase** (PostgreSQL), and **Upstash** (Redis). 

- `build.sh` handles the dependency installation, static file collection, and database migrations.
- `start.sh` boots up the Celery worker and Gunicorn server simultaneously.

See the detailed setup steps inside the included `walkthrough.md` for full instructions on configuring the free tier deployment.

---

*For detailed API documentation, please refer to `API_DOCUMENTATION.md`.*
