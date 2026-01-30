"""
Tenant-specific permissions.

This module contains only Company ownership permission.
For role-based permissions, see staff.api.permissions.
"""
from rest_framework import permissions


class IsCompanyOwner(permissions.BasePermission):
    """
    Permission: User must be the company owner.

    For object-level permission:
    - If object is a Company: user must be the owner
    - If object has .company attribute: user must be the company's owner
    """

    def has_object_permission(self, request, view, obj):
        from tenants.models import Company

        # If obj is a Company, check ownership directly
        if isinstance(obj, Company):
            return obj.owner == request.user

        # If obj has a company attribute, check company ownership
        if hasattr(obj, 'company'):
            return obj.company.owner == request.user

        return False
