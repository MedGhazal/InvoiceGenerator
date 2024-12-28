from django.contrib.admin import (
    register,
    ModelAdmin,
)
from .models import Invoicer
from django.urls import reverse
from django.utils.html import format_html, mark_safe
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
        invoicees = '<ul class="field_ul_table">'
        for invoicee in invoicer.invoicee_set.all():
            invoicees += format_html(
                '<li><a href="{}">{}</a></li>',
                reverse('admin:Invoicee_invoicee_change', args=(invoicee.id,)),
                f'{invoicee.name}',
            )
        invoicees += '</ul>'
        return mark_safe(invoicees)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset

    get_invoicees.short_description = _('INVOICEE')
