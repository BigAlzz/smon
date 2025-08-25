# SMON Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: Heroku Deployment

1. **Create Heroku App**
   ```bash
   heroku create your-app-name
   ```

2. **Set Environment Variables**
   ```bash
   heroku config:set DJANGO_ENVIRONMENT=production
   heroku config:set DJANGO_SECRET_KEY=your-secret-key-here
   heroku config:set DJANGO_DEBUG=False
   heroku config:set DJANGO_ALLOWED_HOSTS=your-app-name.herokuapp.com
   ```

3. **Add PostgreSQL Database**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

5. **Run Migrations**
   ```bash
   heroku run python manage.py migrate
   heroku run python manage.py createsuperuser
   ```

### Option 2: Railway Deployment

1. **Connect GitHub Repository**
   - Go to [Railway.app](https://railway.app)
   - Connect your GitHub account
   - Select the `smon` repository

2. **Set Environment Variables**
   ```
   DJANGO_ENVIRONMENT=production
   DJANGO_SECRET_KEY=your-secret-key-here
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=your-domain.railway.app
   ```

3. **Add PostgreSQL Database**
   - Add PostgreSQL service in Railway
   - Environment variables will be auto-configured

4. **Deploy**
   - Railway will automatically deploy from your main branch

### Option 3: DigitalOcean App Platform

1. **Create App**
   - Go to DigitalOcean App Platform
   - Connect GitHub repository

2. **Configure Build Settings**
   ```yaml
   name: smon
   services:
   - name: web
     source_dir: /
     github:
       repo: BigAlzz/smon
       branch: main
     run_command: gunicorn kpa_monitoring.wsgi:application
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: DJANGO_ENVIRONMENT
       value: production
     - key: DJANGO_SECRET_KEY
       value: your-secret-key-here
   databases:
   - name: db
     engine: PG
     version: "13"
   ```

## 🔧 Environment Variables

### Required Variables
```bash
DJANGO_ENVIRONMENT=production
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Optional Variables
```bash
# Database (if not using platform default)
DATABASE_URL=postgresql://user:pass@localhost/dbname

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# AWS S3 (for file storage)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1

# Redis (for caching)
REDIS_URL=redis://localhost:6379/0
```

## 📋 Post-Deployment Steps

1. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

2. **Load Initial Data**
   ```bash
   python manage.py setup_initial_data
   ```

3. **Collect Static Files** (if needed)
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Test Application**
   - Visit your deployed URL
   - Login with superuser credentials
   - Test key functionality

## 🔒 Security Checklist

- [ ] `DEBUG = False` in production
- [ ] Strong `SECRET_KEY` set
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] HTTPS enabled (SSL certificate)
- [ ] Database credentials secured
- [ ] Environment variables set correctly
- [ ] Static files served properly
- [ ] CSRF protection enabled
- [ ] Security headers configured

## 🚨 Troubleshooting

### Common Issues

1. **Static Files Not Loading**
   - Ensure `STATIC_ROOT` is set
   - Run `collectstatic` command
   - Check web server configuration

2. **Database Connection Errors**
   - Verify `DATABASE_URL` format
   - Check database credentials
   - Ensure database is accessible

3. **CSRF Token Errors**
   - Check `ALLOWED_HOSTS` setting
   - Verify domain configuration
   - Clear browser cache

4. **Permission Errors**
   - Check file permissions
   - Verify user roles in admin
   - Test with superuser account

### Logs and Debugging

```bash
# Heroku logs
heroku logs --tail

# Railway logs
# Available in Railway dashboard

# DigitalOcean logs
# Available in App Platform console
```

## 📞 Support

For deployment issues or questions:
1. Check the logs for error messages
2. Verify environment variables
3. Test locally with production settings
4. Contact the development team

---

**SMON** - Ready for Production Deployment! 🚀
