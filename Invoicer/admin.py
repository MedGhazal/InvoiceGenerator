from django.contrib.admin import (
    register,
    ModelAdmin,
)
from .models import Invoicer, BankAccount, LegalInformation
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _


@register(Invoicer)
class InvoicerAdmin(ModelAdmin):

    list_display = (
        'name',
        'get_invoicees',
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

    get_invoicees.short_description = _('INVOICEE')


@register(BankAccount)
class BankAccountAdmin(ModelAdmin):

    search_fields = ('bankName', 'owner')


@register(LegalInformation)
class LegalInformation(ModelAdmin):

    search_fields = ('invoicer',)
