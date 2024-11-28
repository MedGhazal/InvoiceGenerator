from django.contrib.admin import (
    register,
    ModelAdmin,
    display,
)
from .models import Invoicer
from django.utils.translation import gettext_lazy as _


@register(Invoicer)
class InvoicerAdmin(ModelAdmin):
    list_display = (
        'name',
        'get_invoicees',
        'hasBankData',
        'ice',
    )
    search_fields = ('name',)

    def get_invoicees(self, invoicer):
        invoicees = []
        for invoicee in invoicer.invoicee_set.all():
            invoicees.append(str(invoicee))
        return f'{invoicees}'

    get_invoicees.short_description = _('INVOICEES')
