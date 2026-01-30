from rest_framework import permissions
from staff.models import Employee

class IsCompanyOwner(permissions.BasePermission):
    """
    Permission: User must be the company owner.

    For object-level permission:
    - If object is a Company: user must be the owner
    - If object has .company attribute: user must be the company's owner
    """

    def has_object_permission(self, request, view, obj):
        # If obj is a Company, check ownership directly
        if isinstance(obj, Company):
            return obj.owner == request.user

        # If obj has a company attribute, check company ownership
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user

        return False


class IsCompanyAdmin(permissions.BasePermission):
    """
    Permission: User must be company owner OR admin employee.

    For list views: User must have a company (via request.company from middleware)
    For object views: User must be owner or admin of the object's company
    """

    def has_permission(self, request, view):
        """Check if user has access to any company"""
        if not request.user.is_authenticated:
            return False
        return request.company is not None

    def has_object_permission(self, request, view, obj):
        """Check if user is admin of the object's company"""
        # Get the company from the object
        if isinstance(obj, Company):
            company = obj
        elif hasattr(obj, 'company'):
            company = obj.company
        else:
            return False

        # Check if owner
        if company.owner == request.user:
            return True

        # Check if admin employee
        try:
            if hasattr(request.user, 'employment'):
                employment = request.user.employment
                return (
                    employment.company == company and
                    employment.is_admin() and
                    not employment.is_deleted
                )
        except Employee.DoesNotExist:
            pass

        return False


class IsCompanyMember(permissions.BasePermission):
    """
    Permission: User must be owner or employee of company.

    Less restrictive than IsCompanyAdmin - any member can access.
    """

    def has_permission(self, request, view):
        """Check if user has access to any company"""
        if not request.user.is_authenticated:
            return False
        return request.company is not None

    def has_object_permission(self, request, view, obj):
        """Check if user is member (owner or employee) of the object's company"""
        # Get the company from the object
        if isinstance(obj, Company):
            company = obj
        elif hasattr(obj, 'company'):
            company = obj.company
        else:
            return False

        # Check if owner
        if company.owner == request.user:
            return True

        # Check if employee
        try:
            if hasattr(request.user, 'employment'):
                return (
                    request.user.employment.company == company and
                    not request.user.employment.is_deleted
                )
        except Employee.DoesNotExist:
            pass

        return False


class CanManageEmployees(permissions.BasePermission):
    """
    Permission: User can manage employees (owner or admin role).

    Specialized permission for employee management endpoints.
    """

    def has_permission(self, request, view):
        """Check if user can manage employees"""
        if not request.user.is_authenticated or not request.company:
            return False

        # Owner can always manage employees
        if request.company.owner == request.user:
            return True

        # Admin employees can manage employees
        try:
            if hasattr(request.user, 'employment'):
                employment = request.user.employment
                return (
                    employment.company == request.company and
                    employment.is_admin() and
                    not employment.is_deleted
                )
        except Employee.DoesNotExist:
            pass

        return False

    def has_object_permission(self, request, view, obj):
        """Check if user can manage this specific employee"""
        # Must be employee of same company
        if not isinstance(obj, Employee):
            return False

        if obj.company != request.company:
            return False

        # Owner can manage all employees
        if request.company.owner == request.user:
            return True

        # Admin employees can manage other employees (but not themselves for deletion)
        try:
            if hasattr(request.user, 'employment'):
                employment = request.user.employment
                is_admin = (
                    employment.company == request.company and
                    employment.is_admin() and
                    not employment.is_deleted
                )

                if is_admin:
                    # Admin cannot delete themselves
                    if view.action == 'destroy' and obj.user == request.user:
                        return False
                    return True
        except Employee.DoesNotExist:
            pass

        return False


class HasPermission(permissions.BasePermission):
    """
    Permission: Check if user has specific permission(s).

    Usage in view:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, HasPermission]
            required_permission = 'can_view_all_calendars'

            # Or multiple permissions:
            required_permissions = ['can_book_appointments', 'can_checkout']
    """

    def has_permission(self, request, view):
        """Check if user has required permission(s)"""
        from tenants.permissions_utils import check_permission

        if not request.user.is_authenticated:
            return False

        # Superuser has all permissions
        if request.user.is_superuser:
            return True

        # Get required permission(s)
        required_permission = getattr(view, 'required_permission', None)
        required_permissions = getattr(view, 'required_permissions', [])

        if not required_permission and not required_permissions:
            # No specific permissions required, just needs company access
            return request.company is not None

        # Check single permission
        if required_permission:
            return check_permission(
                request.user,
                required_permission,
                request.company
            )

        # Check multiple permissions (all must pass)
        for perm_field in required_permissions:
            if not check_permission(request.user, perm_field, request.company):
                return False

        return True


class PermissionRequiredMixin:
    """
    Mixin for DRF ViewSets to require specific permissions per action.

    Usage:
        class AppointmentViewSet(PermissionRequiredMixin, viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated]

            # Define permissions per action
            permission_map = {
                'list': 'can_view_own_calendar',
                'retrieve': 'can_view_own_calendar',
                'create': 'can_book_appointments',
                'update': 'can_book_appointments',
                'destroy': 'can_book_appointments',
                'view_all': 'can_view_all_calendars',  # Custom action
            }
    """

    permission_map = {}

    def check_permissions(self, request):
        """Override to add permission checking"""
        from rest_framework.exceptions import PermissionDenied
        from django.utils.translation import gettext_lazy as _
        from tenants.permissions_utils import check_permission

        # First run default permission checks
        super().check_permissions(request)

        # Then check action-specific permission
        action = self.action
        if action in self.permission_map:
            perm_field = self.permission_map[action]
            if not check_permission(request.user, perm_field, request.company):
                self.permission_denied(
                    request,
                    message=_("You do not have permission to perform this action.")
                )
