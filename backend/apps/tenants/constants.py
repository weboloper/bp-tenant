"""
Tenant-specific constants and business rules.

This module contains:
- Feature-to-permission mappings
- Plan-based access control rules
- Default values for tenant provisioning
"""

# Permission fields that require specific plan features
# Format: {'permission_field': 'required_feature_in_plan'}
#
# When a permission check is made for these fields,
# the system will also verify the tenant's plan has the required feature.
#
# Example: 'can_access_insights' requires 'advanced_analytics' feature in plan
FEATURE_RESTRICTED_PERMISSIONS = {
    'can_access_insights': 'advanced_analytics',
    'can_manage_api': 'api_access',
    'can_use_automation': 'automation',
    'can_use_custom_roles': 'custom_roles',
    'can_use_google_calendar': 'google_calendar',
    'can_use_reserve_with_google': 'reserve_with_google',
}

# Permissions that are always available regardless of plan
# (basic operational permissions)
ALWAYS_AVAILABLE_PERMISSIONS = [
    'can_view_own_calendar',
    'can_book_appointments',
    'can_checkout',
    'can_manage_own_profile',
]
