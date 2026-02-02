from django.db import models
from django.utils.translation import gettext_lazy as _
from core.mixins import TenantAwareMixin, SoftDeleteMixin, TimestampMixin
from core.managers import TenantAwareManager, SoftDeleteTenantAwareManager
from django.conf import settings
from core.utils import ValidationUtils
from phonenumber_field.modelfields import PhoneNumberField


class Client(TenantAwareMixin, SoftDeleteMixin, TimestampMixin, models.Model):
    """
    Client model representing a customer in the system.
    Inherits company awareness, soft delete capability, and timestamps.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profiles',
        verbose_name=_("User Account"),
        help_text=_("Linked user account.")
    )

    first_name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Last Name"))
    email = models.EmailField(blank=True, null=True, verbose_name=_("Email"))
    phone = PhoneNumberField(
        region="TR",
        verbose_name=_('Phone'),
        validators=[ValidationUtils.validate_phone_supported],
        blank=True,
        null=True
    )


    gender = models.CharField(
        max_length=20,
        choices=[
            ('female', _('Female')),
            ('male', _('Male')),
            ('unspecified', _('Unspecified')),
        ],
        default='unspecified',
        verbose_name=_("Gender")
    )
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_("Date of Birth"))
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("General notes about the client.")
    )
    
    # Marketing & Status
    accepts_marketing = models.BooleanField(
        default=False,
        verbose_name=_("Accepts Marketing"),
        help_text=_("Does the client consent to receive marketing communications?")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active"),
        help_text=_("Designates whether this client should be treated as active.")
    )
    is_banned = models.BooleanField(
        default=False,
        verbose_name=_("Is Banned"),
        help_text=_("Is this client banned from booking?")
    )
    
    # Source
    # source = models.ForeignKey(
    #     'tenants.ClientSource',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='clients',
    #     verbose_name=_("Source")
    # )

    # Managers
    objects = SoftDeleteTenantAwareManager()
    all_objects = TenantAwareManager()

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['company', 'phone']),
            models.Index(fields=['company', 'email']),
            models.Index(fields=['company', 'is_active']),
        ]

    def __str__(self):
        return self.full_name or (self.phone.as_e164 if self.phone else f"Client #{self.pk}")

    @property
    def full_name(self):
        """Returns full name, handling None values"""
        parts = [self.first_name, self.last_name]
        name = ' '.join(p for p in parts if p)
        return name or None
