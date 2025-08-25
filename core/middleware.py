"""
Custom middleware for KPA Monitoring system

This module provides middleware for audit logging, request tracking,
and security enhancements.
"""

import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from accounts.models import AuditLog


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log all user actions for audit purposes
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Store request start time"""
        request._audit_start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Log the request/response for audit purposes"""
        
        # Skip logging for certain paths
        skip_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/admin/jsi18n/',
        ]
        
        if any(request.path.startswith(path) for path in skip_paths):
            return response
        
        # Skip logging for GET requests to avoid too much noise
        if request.method == 'GET' and not request.path.startswith('/admin/'):
            return response
        
        # Only log for authenticated users
        if isinstance(request.user, AnonymousUser):
            return response
        
        try:
            # Determine action based on method and path
            action = self._determine_action(request.method, request.path, response.status_code)
            
            if action:
                # Get client IP
                ip_address = self._get_client_ip(request)
                
                # Prepare additional data
                additional_data = {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'processing_time': time.time() - getattr(request, '_audit_start_time', time.time())
                }
                
                # Add request data for POST/PUT/PATCH
                if request.method in ['POST', 'PUT', 'PATCH'] and hasattr(request, 'POST'):
                    # Filter out sensitive data
                    post_data = dict(request.POST)
                    sensitive_fields = ['password', 'password1', 'password2', 'csrfmiddlewaretoken']
                    for field in sensitive_fields:
                        if field in post_data:
                            post_data[field] = '[FILTERED]'
                    additional_data['request_data'] = post_data
                
                # Create audit log entry
                AuditLog.objects.create(
                    user=request.user,
                    user_email=request.user.email,
                    user_ip_address=ip_address,
                    action=action,
                    model_name='HTTP_REQUEST',
                    object_id=request.path,
                    object_repr=f"{request.method} {request.path}",
                    additional_data=additional_data,
                    session_key=request.session.session_key
                )
        
        except Exception as e:
            # Don't let audit logging break the application
            pass
        
        return response
    
    def _determine_action(self, method, path, status_code):
        """Determine the action type based on request details"""
        if status_code >= 400:
            return None  # Don't log error responses
        
        if method == 'POST':
            if '/login/' in path:
                return 'LOGIN'
            elif '/logout/' in path:
                return 'LOGOUT'
            elif '/admin/' in path:
                return 'CREATE'
            else:
                return 'CREATE'
        elif method == 'PUT' or method == 'PATCH':
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        
        return None
    
    def _get_client_ip(self, request):
        """Get the client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to responses
    """
    
    def process_response(self, request, response):
        """Add security headers"""
        
        # Content Security Policy
        # Allow jsDelivr CDN for Bootstrap during development; in production prefer self-hosted assets
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "script-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src-elem 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: https://cdn.jsdelivr.net; "
            "connect-src 'self';"
        )
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # X-Frame-Options (already set in settings, but ensuring it's there)
        if 'X-Frame-Options' not in response:
            response['X-Frame-Options'] = 'DENY'
        
        # X-XSS-Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for detailed request logging (for debugging)
    """
    
    def process_request(self, request):
        """Log incoming requests"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            print(f"[REQUEST] {request.method} {request.path} - User: {request.user.username}")
        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # In production, use Redis or database
        super().__init__(get_response)
    
    def process_request(self, request):
        """Check rate limits"""
        
        # Skip rate limiting for certain paths
        skip_paths = ['/static/', '/media/', '/favicon.ico']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get client IP
        ip_address = self._get_client_ip(request)
        
        # Simple rate limiting: 100 requests per minute per IP
        current_time = int(time.time() / 60)  # Current minute
        key = f"{ip_address}:{current_time}"
        
        if key in self.request_counts:
            self.request_counts[key] += 1
        else:
            self.request_counts[key] = 1
            # Clean up old entries
            self._cleanup_old_entries(current_time)
        
        if self.request_counts[key] > 100:
            return JsonResponse(
                {'error': 'Rate limit exceeded. Please try again later.'},
                status=429
            )
        
        return None
    
    def _get_client_ip(self, request):
        """Get the client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _cleanup_old_entries(self, current_time):
        """Remove old rate limit entries"""
        keys_to_remove = []
        for key in self.request_counts:
            if ':' in key:
                _, timestamp = key.split(':')
                if int(timestamp) < current_time - 5:  # Keep last 5 minutes
                    keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.request_counts[key]
