"""
Shared constants used across multiple apps in the project.

✅ ARCHITECTURE: Centralized constants to eliminate magic numbers.

This module contains common choices, configurations, and constants
that are used by multiple models throughout the application.

Following best practices:
- Named constants instead of magic numbers
- Decimal types for precise calculations
- Clear documentation for each constant
- Grouped by functional area
"""

from decimal import Decimal


# ============================================================================
# COLOR CONSTANTS
# ============================================================================

# Color choices with soft pastel hex codes
# Used by: services.ServiceCategory, customers.CustomerTag
COLOR_CHOICES = [
    ('#93C5FD', 'Mavi'),           # Light blue
    ('#3B82F6', 'Koyu Mavi'),      # Blue
    ('#7DD3FC', 'Gök Mavisi'),     # Sky blue
    ('#818CF8', 'İndigo'),         # Indigo
    ('#C4B5FD', 'Lavanta'),        # Lavender
    ('#A78BFA', 'Mor'),            # Purple
    ('#C084FC', 'Leylak'),         # Purple/Pink
    ('#F9A8D4', 'Pembe'),          # Pink
    ('#FB923C', 'Mercan'),         # Orange/Coral
    ('#F97316', 'Kızıl'),          # Deep orange
    ('#FDBA74', 'Turuncu'),        # Light orange
    ('#FCD34D', 'Kehribar'),       # Amber/Yellow
    ('#FDE047', 'Sarı'),           # Yellow
    ('#BEF264', 'Limon Yeşili'),   # Lime
    ('#86EFAC', 'Yeşil'),          # Light green
    ('#5EEAD4', 'Turkuaz'),        # Teal
    ('#67E8F9', 'Camgöbeği'),      # Cyan
]

# Default color for new categories/tags
DEFAULT_COLOR = '#93C5FD'


# ============================================================================
# TENANT PROVISIONING
# ============================================================================

# Trial period for new tenants (days)
DEFAULT_TRIAL_DAYS = 14