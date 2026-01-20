from django.db import models
from django.template import Template, Context
from django.utils.translation import gettext_lazy as _

from core.mixins import TimestampMixin


class BaseTemplate(TimestampMixin, models.Model):
    """
    Abstract base class for all message/notification templates.
    Provides common fields and template rendering functionality.
    """
    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)s_templates',
        verbose_name=_('Company'),
        help_text=_('If null, this is a system-wide template')
    )
    code = models.CharField(
        _('Template Code'),
        max_length=100,
        help_text=_('Unique identifier for this template within the company')
    )
    name = models.CharField(_('Template Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    available_variables = models.JSONField(
        _('Available Variables'),
        default=dict,
        blank=True,
        help_text=_('Dictionary of variable names and their descriptions')
    )
    is_active = models.BooleanField(_('Is Active'), default=True)

    class Meta:
        abstract = True
        unique_together = [('company', 'code')] 

    def __str__(self):
        if self.company:
            return f"{self.company.name} - {self.name}"
        return f"System - {self.name}"

    def render_template(self, template_text, context):
        """
        Render a template string with the given context.

        Args:
            template_text: Django template string
            context: Dictionary of variables to render

        Returns:
            Rendered string or None if template is empty
        """
        if not template_text:
            return None
        return Template(template_text).render(Context(context))
