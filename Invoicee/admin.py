from django.contrib.admin import (
    register,
    ModelAdmin,
    SimpleListFilter,
)
from .models import Invoicee
from Invoicer.models import Invoicer
from django.utils.translation import gettext as _


class InvoicerFilter(SimpleListFilter):
    title = _('INVOICER')
    parameter_name = _('INVOICER')

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicer.id, invoicer.name)
                for invoicer in Invoicer.objects.all().order_by('name')
            ]
        return [
            (invoicer.id, invoicer.name)
            for invoicer in Invoicer.objects.filter(manager=request.user)
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoicer=self.value())


@register(Invoicee)
class InvoiceeAdmin(ModelAdmin):
    list_filter = (
        'country',
        InvoicerFilter,
    )
    list_display = (
        'name',
        'ice',
        'cin',
        'get_balance',
    )
    search_fields = ('name',)
    fields = [
        'invoicer',
        'name',
        'address',
        'cin',
        'ice',
        'is_person',
    ]

    def get_balance(self, invoicee):
        balance = 0
        for invoice in invoicee.invoice_set.filter(draft=False):
            balance += invoice.owedAmount - invoice.paidAmount
        if balance == 0:
            return '-'
        elif invoicee.country.lower() == 'mar':
            return f'{balance}DH'
        elif invoicee.country.lower() == 'fr':
            return f'{balance}€'
        else:
            return ''

    get_balance.short_description = _('TBPaid')

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet.order_by('-id')
        return querySet.filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user),
        ).order_by('-id')

    def has_view_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoicer.manager != request.user
        ):
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoicer.manager != request.user
        ):
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not request.user.is_superuser:
            return False
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'invoicer':
            kwargs['queryset'] = Invoicer.objects.filter(manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
