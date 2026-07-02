# DMResponder Backend Setup Guide

## Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis (for Celery tasks)
- pip or uv package manager

## Installation Steps

### 1. Clone and Navigate to Project
```bash
cd /path/to/dmresponder
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/dmresponder
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 5. Setup PostgreSQL Database
```bash
# Create database
createdb dmresponder

# Or using psql
psql -U postgres
CREATE DATABASE dmresponder;
```

### 6. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser
```bash
python manage.py createsuperuser
```

### 8. Start Development Server
```bash
python manage.py runserver 0.0.0.0:8000
```

### 9. Start Redis (Optional, for Celery)
```bash
redis-server
```

### 10. Start Celery Worker (Optional)
```bash
celery -A dmresponder worker -l info
```

## API Access

### Login to Admin Panel
```
http://localhost:8000/admin/
```

### API Documentation
```
http://localhost:8000/api/
```

### Get JWT Token
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

## Frontend Integration

The frontend should be configured to use the following API base URL:
```
http://localhost:8000/api/
```

### CORS Configuration
Make sure to update `CORS_ALLOWED_ORIGINS` in `.env` to include your frontend URL.

## Database Schema

The project uses PostgreSQL with the following main models:

- **User**: Django built-in user model
- **Profile**: Extended user profile
- **InstagramAccount**: Instagram account connections
- **FacebookPage**: Facebook page connections
- **WhatsAppAccount**: WhatsApp Business account connections
- **AutomationWorkflow**: Automation workflow definitions
- **Lead**: CRM leads
- **Broadcast**: Broadcast campaigns
- **Conversation**: Message conversations
- **AnalyticsEvent**: Event tracking

## Troubleshooting

### Database Connection Error
Ensure PostgreSQL is running and the `DATABASE_URL` in `.env` is correct.

### CORS Error
Update `CORS_ALLOWED_ORIGINS` in `.env` to include your frontend URL.

### Module Not Found
Run `pip install -r requirements.txt` again to ensure all dependencies are installed.

## Production Deployment

For production, use:
- Gunicorn as the WSGI server
- Nginx as the reverse proxy
- PostgreSQL for database
- Redis for caching and Celery
- WhiteNoise for static files

Example Gunicorn command:
```bash
gunicorn dmresponder.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

