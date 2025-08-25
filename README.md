# SMON - Strategic Monitoring System

A comprehensive KPA (Key Performance Area) Performance Monitoring Application for GCRA (Gauteng City-Region Academy).

## 🚀 Features

### Core Functionality
- **KPA Management**: Create, track, and monitor Key Performance Areas
- **Progress Tracking**: Real-time progress monitoring with visual indicators
- **User Management**: Role-based access control with multiple user types
- **Organizational Structure**: Hierarchical org chart with staff management
- **Dashboard Analytics**: Executive dashboard with performance metrics
- **Reporting System**: Comprehensive reporting and data export

### User Roles
- **System Admin**: Full system access and user management
- **Senior Manager**: Department oversight and reporting
- **Programme Manager**: Programme-specific KPA management
- **M&E Strategy**: Monitoring and evaluation focus
- **Staff Member**: Basic access and profile management

### Key Features
- **Form Error Highlighting**: Visual validation feedback for better UX
- **Dark/Light Theme**: User preference-based theming
- **Responsive Design**: Mobile-friendly interface
- **Audit Logging**: Comprehensive activity tracking
- **Notification System**: Real-time updates and alerts

## 🛠️ Technology Stack

- **Backend**: Django 4.2.7
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, JavaScript
- **Authentication**: Django Auth with JWT support
- **API**: Django REST Framework
- **Styling**: Custom CSS with Bootstrap integration

## 📦 Installation

### Prerequisites
- Python 3.11+
- pip
- virtualenv (recommended)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/BigAlzz/smon.git
   cd smon
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   # Create .env file (optional)
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=True
   DJANGO_ENVIRONMENT=development
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py loaddata fixtures/initial_data.json
   python manage.py createsuperuser
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

7. **Access Application**
   - Open browser to `http://127.0.0.1:8000`
   - Login with superuser credentials

## 🚀 Deployment

### Production Settings
The application is configured for production deployment with:
- Environment-based configuration
- Security headers and CSRF protection
- Static file handling
- Database connection pooling ready

### Environment Variables
```bash
DJANGO_ENVIRONMENT=production
DJANGO_SECRET_KEY=your-production-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## 📱 Usage

### Getting Started
1. **Login**: Use your credentials to access the system
2. **Profile Setup**: Complete your user profile information
3. **Dashboard**: View your personalized dashboard
4. **KPA Management**: Create and track Key Performance Areas
5. **Progress Updates**: Regular progress reporting and monitoring

### Key Workflows
- **KPA Creation**: Define objectives, targets, and timelines
- **Progress Tracking**: Update progress with evidence and comments
- **Team Management**: Assign responsibilities and monitor team performance
- **Reporting**: Generate comprehensive performance reports

## 🔧 Development

### Project Structure
```
smon/
├── accounts/          # User management and authentication
├── core/             # Core functionality and models
├── kpas/             # KPA management
├── progress/         # Progress tracking
├── reports/          # Reporting system
├── notifications/    # Notification system
├── operational_plan/ # Operational planning
├── static/           # Static files (CSS, JS, images)
├── templates/        # HTML templates
└── manage.py         # Django management script
```

### Key Components
- **Error Highlighting**: Advanced form validation with visual feedback
- **Role-Based Access**: Comprehensive permission system
- **Audit Trail**: Complete activity logging
- **API Integration**: RESTful API for external integrations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software developed for GCRA.

## 📞 Support

For support and questions, please contact the development team.

---

**SMON** - Strategic Monitoring for Performance Excellence
