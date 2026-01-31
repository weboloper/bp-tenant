"""
Permission utility functions for checking user permissions.

This module provides helper functions for checking user permissions
in views, APIs, and business logic.

Usage:
    from staff.permissions_utils import check_permission, require_permission

    # In function-based view
    @require_permission('can_view_all_calendars')
    def appointments_view(request):
        # User is guaranteed to have permission here
        pass

    # In class-based view
    def get(self, request):
        if check_permission(request.user, 'can_view_all_calendars'):
            # Show all calendars
        else:
            # Show only own calendar
"""

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _


def get_user_company(user):
    """
    Get company for user (owner or employee).

    Args:
        user: User instance

    Returns:
        Company instance or None

    Logic:
    - If user owns a company → return owned company
    - If user is an employee → return employment company
    - Otherwise → return None
    """
    if not user or not user.is_authenticated:
        return None

    # Check if owner
    try:
        owned_company = user.owned_companies.filter(
            is_deleted=False,
            is_active=True
        ).first()
        if owned_company:
            return owned_company
    except Exception:
        pass

    # Check if employee
    try:
        if hasattr(user, 'employment'):
            employment = user.employment
            if not employment.is_deleted and employment.company.is_active:
                return employment.company
    except Exception:
        pass

    return None


def get_user_employee(user, company=None):
    """
    Get Employee instance for user.

    Args:
        user: User instance
        company: Optional Company instance to check against

    Returns:
        Employee instance or None
    """
    if not user or not user.is_authenticated:
        return None

    try:
        if hasattr(user, 'employment'):
            employment = user.employment
            if not employment.is_deleted:
                if company and employment.company != company:
                    return None
                return employment
    except Exception:
        pass

    return None


def check_permission(user, permission_field, company=None):
    """
    Check if user has a specific permission.

    Args:
        user: User instance
        permission_field: Permission field name (e.g., 'can_view_all_calendars')
        company: Optional Company instance (if None, uses user's company)

    Returns:
        Boolean

    Logic:
    1. If user is superuser → True (bypass all checks)
    2. Check plan-based feature restriction (if applicable)
    3. If user is owner of the company → True (owner has all permissions)
    4. If user is employee → check CompanyRolePermission
    5. Otherwise → False
    """
    # Lazy imports to avoid circular dependencies
    from staff.models import CompanyRolePermission
    from staff.constants import FEATURE_RESTRICTED_PERMISSIONS

    if not user or not user.is_authenticated:
        return False

    # Superuser has all permissions
    if user.is_superuser:
        return True

    # Get company
    if company is None:
        company = get_user_company(user)

    if not company:
        return False

    # Check plan-based feature restriction
    if permission_field in FEATURE_RESTRICTED_PERMISSIONS:
        required_feature = FEATURE_RESTRICTED_PERMISSIONS[permission_field]
        if not _check_plan_feature(company, required_feature):
            return False  # Plan doesn't include this feature

    # Owner has all permissions (that pass plan check)
    if company.is_owner(user):
        return True

    # Check employee permissions
    employee = get_user_employee(user, company)
    if not employee:
        return False

    try:
        perms = CompanyRolePermission.objects.get(
            company=company,
            level=employee.role_level
        )
        return getattr(perms, permission_field, False)
    except CompanyRolePermission.DoesNotExist:
        return False


def _check_plan_feature(company, feature_name):
    """
    Check if company's subscription plan includes a specific feature.

    Args:
        company: Company instance
        feature_name: Feature key to check (e.g., 'advanced_analytics')

    Returns:
        Boolean - True if plan has the feature, False otherwise
    """
    try:
        from billing.models import TenantSubscription
        subscription = TenantSubscription.objects.select_related('plan').get(
            tenant=company,
            status='active'
        )
        return subscription.plan.has_feature(feature_name)
    except TenantSubscription.DoesNotExist:
        return False
    except Exception:
        return False


def get_user_permissions(user, company=None):
    """
    Get CompanyRolePermission object for user.

    Args:
        user: User instance
        company: Optional Company instance (if None, uses user's company)

    Returns:
        CompanyRolePermission instance or None
    """
    from staff.models import CompanyRolePermission

    if not user or not user.is_authenticated:
        return None

    # Superuser: return None (has all permissions anyway)
    if user.is_superuser:
        return None

    # Get company
    if company is None:
        company = get_user_company(user)

    if not company:
        return None

    # Owner: return None (has all permissions anyway)
    if company.is_owner(user):
        return None

    # Get employee permissions
    employee = get_user_employee(user, company)
    if not employee:
        return None

    try:
        return CompanyRolePermission.objects.get(
            company=company,
            level=employee.role_level
        )
    except CompanyRolePermission.DoesNotExist:
        return None


def require_company(view_func):
    """
    Decorator: Require user to have company access.

    Raises PermissionDenied (403) if user has no company.

    Usage:
        @require_company
        def my_view(request):
            company = request.company  # Guaranteed to exist
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied(_("Authentication required."))

        # Superuser can access (middleware sets request.company)
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        if not request.company:
            raise PermissionDenied(_("No company access."))

        return view_func(request, *args, **kwargs)

    return wrapper


def require_permission(permission_field):
    """
    Decorator: Require user to have specific permission.

    Args:
        permission_field: Permission field name (e.g., 'can_view_all_calendars')

    Raises PermissionDenied (403) if user lacks permission.

    Usage:
        @require_permission('can_view_all_calendars')
        def appointments_view(request):
            # User is guaranteed to have permission
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied(_("Authentication required."))

            # Check permission
            if not check_permission(request.user, permission_field, request.company):
                raise PermissionDenied(
                    _("You do not have permission to perform this action.")
                )

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_permissions(permission_fields):
    """
    Decorator: Require user to have ALL specified permissions.

    Args:
        permission_fields: List of permission field names

    Raises PermissionDenied (403) if user lacks any permission.

    Usage:
        @require_permissions(['can_book_appointments', 'can_checkout'])
        def booking_checkout_view(request):
            # User has both permissions
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied(_("Authentication required."))

            # Check all permissions
            for perm_field in permission_fields:
                if not check_permission(request.user, perm_field, request.company):
                    raise PermissionDenied(
                        _("You do not have permission to perform this action.")
                    )

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
