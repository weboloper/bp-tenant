from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    # Settings
    BusinessSettingsViewSet,
    CalendarSettingsViewSet,
    WaitlistSettingsViewSet,
    OnlineBookingSettingsViewSet,
    ReceiptSettingsViewSet,
    TippingSettingsViewSet,
    GiftCardSettingsViewSet,
    TimesheetSettingsViewSet,
    PayRunSettingsViewSet,
    CommissionSettingsViewSet,
    PinSwitchingSettingsViewSet,
    # Lookups
    ClientSourceViewSet,
    BlockedTimeTypeViewSet,
    AppointmentStatusViewSet,
    PaymentMethodViewSet,
    CancellationReasonViewSet,
    TimeOffTypeViewSet,
    # Data
    LocationViewSet,
    TaxRateViewSet,
    ServiceChargeViewSet,
    ClosedPeriodViewSet,
    ResourceViewSet,
)

router = DefaultRouter()

# =============================================================================
# SETTINGS (Singleton - no list, only retrieve/update via /settings/{type}/)
# =============================================================================
# These are registered without basename suffix for cleaner URLs

# =============================================================================
# LOOKUPS (System + Custom entries)
# =============================================================================
router.register(r'client-sources', ClientSourceViewSet, basename='client-source')
router.register(r'blocked-time-types', BlockedTimeTypeViewSet, basename='blocked-time-type')
router.register(r'appointment-statuses', AppointmentStatusViewSet, basename='appointment-status')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'cancellation-reasons', CancellationReasonViewSet, basename='cancellation-reason')
router.register(r'time-off-types', TimeOffTypeViewSet, basename='time-off-type')

# =============================================================================
# DATA (Full CRUD)
# =============================================================================
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'tax-rates', TaxRateViewSet, basename='tax-rate')
router.register(r'service-charges', ServiceChargeViewSet, basename='service-charge')
router.register(r'closed-periods', ClosedPeriodViewSet, basename='closed-period')
router.register(r'resources', ResourceViewSet, basename='resource')


# Settings singleton URLs (custom pattern for GET/PATCH on singleton)
settings_patterns = [
    path('business/', BusinessSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-business'),
    path('calendar/', CalendarSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-calendar'),
    path('waitlist/', WaitlistSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-waitlist'),
    path('booking/', OnlineBookingSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-booking'),
    path('receipt/', ReceiptSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-receipt'),
    path('tipping/', TippingSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-tipping'),
    path('gift-card/', GiftCardSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-gift-card'),
    path('timesheet/', TimesheetSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-timesheet'),
    path('pay-run/', PayRunSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-pay-run'),
    path('commission/', CommissionSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-commission'),
    path('pin-switching/', PinSwitchingSettingsViewSet.as_view({
        'get': 'retrieve',
        'patch': 'update',
    }), name='settings-pin-switching'),
]

urlpatterns = [
    path('settings/', include(settings_patterns)),
    path('', include(router.urls)),
]

"""
ENDPOINT REFERENCE:

SETTINGS (Singleton per tenant):
    GET/PATCH  /api/v1/config/settings/business/
    GET/PATCH  /api/v1/config/settings/calendar/
    GET/PATCH  /api/v1/config/settings/waitlist/
    GET/PATCH  /api/v1/config/settings/booking/
    GET/PATCH  /api/v1/config/settings/receipt/
    GET/PATCH  /api/v1/config/settings/tipping/
    GET/PATCH  /api/v1/config/settings/gift-card/
    GET/PATCH  /api/v1/config/settings/timesheet/
    GET/PATCH  /api/v1/config/settings/pay-run/
    GET/PATCH  /api/v1/config/settings/commission/
    GET/PATCH  /api/v1/config/settings/pin-switching/

LOOKUPS (System + Custom, DELETE only for custom):
    GET/POST   /api/v1/config/client-sources/
    GET/PATCH  /api/v1/config/client-sources/{id}/
    DELETE     /api/v1/config/client-sources/{id}/  (only is_system=False)

    GET/POST   /api/v1/config/blocked-time-types/
    GET/PATCH  /api/v1/config/blocked-time-types/{id}/
    DELETE     /api/v1/config/blocked-time-types/{id}/

    GET/POST   /api/v1/config/appointment-statuses/
    GET/PATCH  /api/v1/config/appointment-statuses/{id}/
    DELETE     /api/v1/config/appointment-statuses/{id}/

    GET/POST   /api/v1/config/payment-methods/
    GET/PATCH  /api/v1/config/payment-methods/{id}/
    DELETE     /api/v1/config/payment-methods/{id}/

    GET/POST   /api/v1/config/cancellation-reasons/
    GET/PATCH  /api/v1/config/cancellation-reasons/{id}/
    DELETE     /api/v1/config/cancellation-reasons/{id}/

    GET/POST   /api/v1/config/time-off-types/
    GET/PATCH  /api/v1/config/time-off-types/{id}/
    DELETE     /api/v1/config/time-off-types/{id}/

DATA (Full CRUD):
    GET/POST   /api/v1/config/locations/
    GET        /api/v1/config/locations/active/
    GET/PATCH  /api/v1/config/locations/{id}/
    DELETE     /api/v1/config/locations/{id}/

    GET/POST   /api/v1/config/tax-rates/
    GET/PATCH  /api/v1/config/tax-rates/{id}/
    POST       /api/v1/config/tax-rates/{id}/set_default/
    DELETE     /api/v1/config/tax-rates/{id}/

    GET/POST   /api/v1/config/service-charges/
    GET/PATCH  /api/v1/config/service-charges/{id}/
    DELETE     /api/v1/config/service-charges/{id}/

    GET/POST   /api/v1/config/closed-periods/
    GET        /api/v1/config/closed-periods/upcoming/
    GET/PATCH  /api/v1/config/closed-periods/{id}/
    DELETE     /api/v1/config/closed-periods/{id}/

    GET/POST   /api/v1/config/resources/
    GET        /api/v1/config/resources/active/
    GET        /api/v1/config/resources/?location={id}
    GET/PATCH  /api/v1/config/resources/{id}/
    DELETE     /api/v1/config/resources/{id}/
"""
