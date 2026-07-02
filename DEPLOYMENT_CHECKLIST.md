# DMResponder Deployment Checklist

## Pre-Deployment

- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured in `.env`
- [ ] PostgreSQL database created and migrations applied
- [ ] Superuser account created
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Tests passed (`python manage.py test`)

## Database

- [ ] PostgreSQL 13+ installed and running
- [ ] Database created: `dmresponder`
- [ ] Migrations applied: `python manage.py migrate`
- [ ] Backup strategy in place

## Security

- [ ] `DEBUG=False` in production
- [ ] `SECRET_KEY` is strong and unique
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] HTTPS enabled (SSL certificate)
- [ ] CORS origins restricted to frontend domain
- [ ] Database credentials secured (not in git)

## Backend Services

- [ ] Gunicorn or similar WSGI server configured
- [ ] Redis running for caching and Celery
- [ ] Celery worker running for background tasks
- [ ] Nginx or Apache reverse proxy configured

## Frontend Integration

- [ ] Frontend API base URL points to backend
- [ ] CORS headers properly configured
- [ ] JWT token refresh mechanism working
- [ ] Error handling for API failures

## Monitoring

- [ ] Logging configured
- [ ] Error tracking (Sentry or similar)
- [ ] Performance monitoring
- [ ] Database backups scheduled

## Post-Deployment

- [ ] Test login functionality
- [ ] Test API endpoints
- [ ] Test automation workflows
- [ ] Monitor error logs
- [ ] Performance testing

## Rollback Plan

- [ ] Database backup before deployment
- [ ] Previous version available for rollback
- [ ] Rollback procedure documented
