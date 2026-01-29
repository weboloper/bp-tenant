"""
Custom decorators for common functionality
"""
import functools
import logging
from typing import Callable, Any
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


def handle_errors(error_message: str = "Bir hata oluştu"):
    """Decorator to handle exceptions gracefully"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                if hasattr(args[0], 'META'):  # Django request object
                    return JsonResponse({
                        'success': False,
                        'error': error_message
                    }, status=500)
                raise
        return wrapper
    return decorator


def cache_result(timeout: int = 300, key_prefix: str = ''):
    """Cache function results"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def ajax_required(func: Callable) -> Callable:
    """Decorator to ensure request is AJAX"""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Bu endpoint sadece AJAX istekleri kabul eder'
            }, status=400)
        return func(request, *args, **kwargs)
    return wrapper


def api_key_required(func: Callable) -> Callable:
    """Simple API key authentication decorator"""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        if not api_key:
            return JsonResponse({
                'success': False,
                'error': 'API key gerekli'
            }, status=401)
        
        # Here you would validate the API key
        # For now, just check if it exists
        # In real implementation, check against database
        
        return func(request, *args, **kwargs)
    return wrapper


def log_execution(log_level: int = logging.INFO):
    """Log function execution with timing"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            logger.log(log_level, f"Starting execution of {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.log(log_level, f"Completed {func.__name__} in {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Error in {func.__name__} after {execution_time:.2f}s: {str(e)}")
                raise
        return wrapper
    return decorator


def staff_required(func: Callable) -> Callable:
    """Decorator to require staff status"""
    @functools.wraps(func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Bu işlem için staff yetkisi gerekli'
            }, status=403)
        return func(request, *args, **kwargs)
    return wrapper


# Rate limiting decorators
def rate_limit_api(group: str = 'api', rate: str = '100/h'):
    """Rate limit decorator for API endpoints"""
    def decorator(func: Callable) -> Callable:
        @ratelimit(group=group, key='ip', rate=rate, method='ALL')
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if getattr(request, 'limited', False):
                return JsonResponse({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.'
                }, status=429)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# PLAN/SUBSCRIPTION DECORATORS
# =============================================================================

def plan_required(module_name: str):
    """
    Decorator to check if the company's subscription plan has access to a module.

    Use this decorator on function-based views that require a specific plan feature.
    The view will return 403 Forbidden if the company's plan doesn't include
    the required module.

    Args:
        module_name: The module/feature to check for. Available options:
            - 'services': Service definition and management
            - 'products': Product management with stock tracking
            - 'pos': Point of sale
            - 'marketing': Campaigns and promotions
            - 'reports': Basic reports
            - 'advanced_reports': Detailed analytics
            - 'advanced_clients': Client segmentation, loyalty, referrals
            - 'advanced_permissions': Custom roles, detailed permissions
            - 'online_booking': Online appointment booking
            - 'multi_location': Multiple business locations
            - 'sms': SMS notifications
            - 'email': Email notifications
            - 'whatsapp': WhatsApp integration
            - 'google_calendar': Google Calendar sync
            - 'reserve_with_google': Reserve with Google

    Usage:
        @api_view(['GET'])
        @plan_required('services')
        def service_list(request):
            ...

        @api_view(['POST'])
        @plan_required('products')
        def update_stock(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            from rest_framework.response import Response
            from rest_framework import status
            from django.utils.translation import gettext_lazy as _

            # Get company from user or request
            company = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                company = getattr(request.user, 'company', None)
            if not company:
                company = getattr(request, 'company', None)

            if company:
                # Check if company has active subscription with the required module
                subscription = getattr(company, 'subscription', None)
                if subscription and subscription.plan:
                    if not subscription.plan.has_module(module_name):
                        return Response(
                            {
                                'detail': str(_(
                                    "Your plan doesn't include the %(module)s module. "
                                    "Please upgrade your subscription."
                                ) % {'module': module_name}),
                                'code': 'plan_feature_required',
                                'required_module': module_name
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def plan_limit_check(limit_name: str, get_count_func: Callable = None):
    """
    Decorator to check plan limits before creating new resources.

    Use this decorator on function-based views that create resources subject to limits.
    The view will return 403 Forbidden if the company has reached their plan limit.

    Args:
        limit_name: The limit to check. Available options:
            - 'employees': Maximum team members
            - 'locations': Maximum business locations
            - 'appointments' or 'appointments_per_month': Monthly appointments
            - 'products': Maximum products
            - 'services': Maximum services

        get_count_func: Optional function that takes (company) and returns current count.
                       If not provided, the check will only verify the limit exists.

    Usage:
        def get_employee_count(company):
            return Employee.objects.filter(company=company).count()

        @api_view(['POST'])
        @plan_limit_check('employees', get_employee_count)
        def create_employee(request):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            from rest_framework.response import Response
            from rest_framework import status
            from django.utils.translation import gettext_lazy as _

            # Get company from user or request
            company = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                company = getattr(request.user, 'company', None)
            if not company:
                company = getattr(request, 'company', None)

            if company:
                subscription = getattr(company, 'subscription', None)
                if subscription and subscription.plan:
                    plan = subscription.plan

                    # Get current count if function provided
                    current_count = 0
                    if get_count_func:
                        current_count = get_count_func(company)

                    # Check if within limit
                    if not plan.check_limit(limit_name, current_count):
                        limit_value = plan.get_limit(limit_name)
                        return Response(
                            {
                                'detail': str(_(
                                    "You have reached your plan limit for %(resource)s. "
                                    "Your plan allows %(limit)s %(resource)s. "
                                    "Please upgrade your subscription."
                                ) % {'resource': limit_name, 'limit': limit_value}),
                                'code': 'plan_limit_exceeded',
                                'limit_name': limit_name,
                                'limit_value': limit_value,
                                'current_count': current_count
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )

            return func(request, *args, **kwargs)
        return wrapper
    return decorator