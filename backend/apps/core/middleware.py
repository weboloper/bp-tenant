import threading
from django.utils.deprecation import MiddlewareMixin


# Thread-local storage for current company context
_thread_locals = threading.local()


def get_current_company():
    """
    Get the current company from thread-local storage.

    Returns:
        Company object or None
    """
    return getattr(_thread_locals, 'company', None)


def set_current_company(company):
    """
    Set the current company in thread-local storage.

    Args:
        company: Company object or None
    """
    _thread_locals.company = company


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to identify and set the current tenant (company) based on the logged-in user.

    Logic for regular users:
    1. If user owns a company (active, not deleted) → use owned company
    2. Else if user is an employee → use employment company
    3. Else → no company (request.company = None)

    Logic for superuser/staff (when SUPERUSER_BYPASS_TENANT=True):
    1. Check for X-Company-ID header → use specified company
    2. Check for session 'selected_company_id' → use stored company
    3. Fallback to regular logic

    Sets:
    - request.company: Company object or None
    - request.is_impersonating: Boolean (True if admin selected a company)
    - Thread-local storage: For use in managers

    Usage:
        Add to MIDDLEWARE in settings.py after AuthenticationMiddleware:
        'core.middleware.TenantMiddleware',
    """

    def process_request(self, request):
        """
        Process the incoming request and set the company context.

        Args:
            request: HttpRequest object
        """
        from django.conf import settings

        company = None
        is_impersonating = False

        if request.user and request.user.is_authenticated:
            # Check if superuser/staff can bypass tenant restrictions
            can_bypass = getattr(settings, 'SUPERUSER_BYPASS_TENANT', True)
            is_admin = request.user.is_superuser or request.user.is_staff

            if is_admin and can_bypass:
                # Admin users can select any company
                company = self._get_admin_selected_company(request)
                if company:
                    is_impersonating = True

            # If admin didn't select a company, or user is not admin, use regular logic
            if not company:
                company = self._get_user_company(request.user)

        # Set company on request object
        request.company = company
        request.is_impersonating = is_impersonating

        # Set in thread-local storage for use in managers
        set_current_company(company)

    def _get_admin_selected_company(self, request):
        """
        Get company selected by admin user via header or session.

        Priority:
        1. X-Company-ID header (for API calls)
        2. Session 'selected_company_id' (for web interface)

        Args:
            request: HttpRequest object

        Returns:
            Company object or None
        """
        from tenants.models import Company

        company_id = None

        # Priority 1: Check X-Company-ID header (useful for API clients)
        company_id = request.META.get('HTTP_X_COMPANY_ID')

        # Priority 2: Check session (useful for admin panel)
        if not company_id and hasattr(request, 'session'):
            company_id = request.session.get('selected_company_id')

        if company_id:
            try:
                # Allow access to deleted companies for admin users
                return Company.all_objects.get(id=company_id)
            except (Company.DoesNotExist, ValueError):
                # Invalid company ID, clear from session
                if hasattr(request, 'session') and 'selected_company_id' in request.session:
                    del request.session['selected_company_id']

        return None

    def _get_user_company(self, user):
        """
        Get company for regular user based on ownership or employment.

        Args:
            user: User object

        Returns:
            Company object or None
        """
        try:
            # Priority 1: Check if user owns a company
            owned_company = user.owned_companies.filter(
                is_deleted=False,
                is_active=True
            ).first()

            if owned_company:
                return owned_company

            # Priority 2: Check if user is an employee
            try:
                employment = user.employment
                if employment and not employment.is_deleted:
                    # Ensure the company is active and not deleted
                    if employment.company.is_active and not employment.company.is_deleted:
                        return employment.company
            except Exception:
                # Employee relation doesn't exist or error accessing it
                pass
        except Exception:
            # Handle any unexpected errors gracefully
            pass

        return None

    def process_response(self, request, response):
        """
        Clean up thread-local storage after request is processed.

        Args:
            request: HttpRequest object
            response: HttpResponse object

        Returns:
            HttpResponse object
        """
        # Clear thread-local storage after request
        if hasattr(_thread_locals, 'company'):
            del _thread_locals.company
        return response

    def process_exception(self, request, exception):
        """
        Clean up thread-local storage if an exception occurs.

        Args:
            request: HttpRequest object
            exception: Exception that occurred

        Returns:
            None (allows exception to propagate)
        """
        # Clear thread-local storage on exception
        if hasattr(_thread_locals, 'company'):
            del _thread_locals.company
        return None
