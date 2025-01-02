from datetime import date, timedelta
from csv import DictWriter
from os import getcwd, remove
from os.path import join
from decimal import Decimal
from tempfile import (
    SpooledTemporaryFile,
)
from zipfile import (
    ZIP_DEFLATED,
    ZipFile,
)
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib.admin import (
    action,
    register,
    display,
    ModelAdmin,
    SimpleListFilter,
    StackedInline,
)
from django.http import (
    HttpResponse,
)
from django.contrib.messages import error, warning
from django.db.models import F

from rangefilter.filters import DateRangeFilter

from Invoicee.models import Invoicee
from Invoicer.models import Invoicer
from .models import Invoice, Project, Fee, Payment
from .utils import (
    create_credit_note,
    generate_invoice_file,
    export_invoice_data,
    LateXError,
)
from InvoiceGenerator.settings import TEMPTEXFILESDIR, EXPORT_DATA_HEADER
from Core.utils import (
    get_currency_symbol,
)


@action(description=_('InvoiceCreateCreditNoteAction'))
def create_credit_note_action(invoiceAdmin, request, queryset):
    for invoice in queryset:
        create_credit_note(invoice)


@action(description=_('InvoiceGenerateAction'))
def generate_invoice(invoiceAdmin, request, querySet):
    with SpooledTemporaryFile() as temporaryFile:
        with ZipFile(temporaryFile, 'w', ZIP_DEFLATED) as archive:
            for invoice in querySet:
                try:
                    file = generate_invoice_file(invoice)
                    pathToFile = join(getcwd(), TEMPTEXFILESDIR, file)
                    archive.write(pathToFile, file)
                    remove(pathToFile)
                except LateXError as e:
                    error(request, ' '.join(e.args))
                    return None
            temporaryFile.seek(0)
            response = HttpResponse(temporaryFile.read())
            response['Content-Disposition'] = 'attachment; filename="pdfs.zip"'
            return response


@action(description=_('InvoicesDataExportAction'))
def export_invoices(invoiceAdmin, request, querySet):
    if request.user.is_superuser:
        with SpooledTemporaryFile(
            mode='w',
            encoding='utf-8',
            newline='',
        ) as temporaryFile:
            dictWriter = DictWriter(temporaryFile, EXPORT_DATA_HEADER)
            dictWriter.writeheader()
            for invoice in querySet:
                if invoice.state == 0:
                    error(request, _('TheQUERYSETHasADraft'))
                    return None
                data = export_invoice_data(invoice, EXPORT_DATA_HEADER)
                dictWriter.writerows(data)
            temporaryFile.seek(0)
            response = HttpResponse(temporaryFile.read())
            response['Content-Disposition'] = 'attachment; filename="export.csv"'
            return response
    else:
        warning(request, _('InvoiceDataExportActionReservedWarning'))
        return None


@action(description=_('InvoiceValidateAction'))
def validate_invoices(invoiceAdmin, request, querySet):
    for invoice in querySet:
        invoice.state = 1
        invoice.save()


class InvoiceStatusFilter(SimpleListFilter):
    title = _('Status')
    parameter_name = _('Status')

    def lookups(self, request, model_admin):
        return [
            (0, _('Draft')),
            (1, _('Validated')),
            (2, _('Paid')),
            (3, _('OverDue')),
            (4, _('LongOverDue')),
        ]

    def queryset(self, request, querySet):
        if self.value() == '0':
            return querySet.filter(status=0)
        elif self.value() == '1':
            return querySet.filter(status=1)
        elif self.value() == '2':
            return querySet.filter(status=2)
        elif self.value() == '3':
            return querySet.filter(
                status=3
            ).filter(
                dueDate__lte=date.today()
            ).filter(
                dueDate__gte=date.today() - timedelta(days=16)
            )
        elif self.value() == '4':
            return querySet.filter(status=3).filter(
                dueDate__lte=date.today() - timedelta(days=15)
            )
        else:
            return None


class InvoiceInvoiceeFilter(SimpleListFilter):
    title = _('INVOICEE')
    parameter_name = _('INVOICEE')

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicee.id, invoicee.name)
                for invoicee in Invoicee.objects.all().order_by('name')
            ]
        return [
            (invoicee.id, invoicee.name)
            for invoicee in Invoicee.objects.filter(
                invoicer__in=Invoicer.objects.filter(
                    manager=request.user
                )
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoicee=self.value())


class InvoiceInvoicerFilter(SimpleListFilter):
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
            for invoicer in Invoicer.objects.filter(
                manager=request.user
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoicer=self.value())


class FeeStackedInline(StackedInline):
    model = Fee
    extra = 0
    min_num = 1

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request)
        if not request.user.is_superuser:
            fields.remove('bookKeepingAmount')
        return fields


@register(Invoice)
class InvoiceAdmin(ModelAdmin):

    list_per_page = 25
    actions = [
        generate_invoice,
        export_invoices,
        validate_invoices,
        create_credit_note_action,
    ]
    list_filter = (
        ('facturationDate', DateRangeFilter),
        InvoiceStatusFilter,
        InvoiceInvoicerFilter,
        InvoiceInvoiceeFilter,
    )
    list_display = (
        '__str__',
        'get_projects',
        'get_fees',
        'dueDate',
        'facturationDate',
        'get_balance',
    )
    autocomplete_fields = ('invoicee',)
    search_fields = ('invoicer__name', 'invoicee__name')
    readonly_fields = []

    def save_model(self, request, invoice, form, change):
        if 'invoicer' not in form.fields:
            invoice.invoicer = Invoicer.objects.get(manager=request.user)
        invoice.save()

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user),
        ).order_by('-id')

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            return (
                request.user.is_superuser
                or obj.invoicer.manager == request.user
            )
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.invoicer.manager == request.user
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.invoicer.manager == request.user
                and not obj.paymentInvoice.exists()
            )
        return True

    def get_fields(self, request, invoice=None):
        fields = super().get_fields(request)
        if not request.user.is_superuser:
            fields.remove('owedAmount')
            fields.remove('paidAmount')
            if Invoicer.objects.filter(manager=request.user).count() == 1:
                fields.remove('invoicer')
            fields.remove('count')
            fields.remove('salesAccount')
            fields.remove('vatAccount')
        return fields

    def get_readonly_fields(self, request, invoice=None):
        fields = super().get_readonly_fields(request)
        return set(fields)

    @display(ordering='owedAmount')
    def get_balance(self, invoice):
        if invoice.state == 0:
            return _('IsDraft')
        balance = invoice.owedAmount - invoice.paidAmount
        if balance <= 0:
            return '-'
        elif invoice.invoicee.country.lower() == 'mar':
            return f'{balance}DH'
        elif invoice.invoicee.country.lower() == 'fr':
            return f'{balance}€'
        return None

    get_balance.short_description = _('TBPaid')

    def get_projects(self, invoice):
        projects = '<ul class="field_ul_table">'
        for project in invoice.project_set.all():
            projects += format_html(
                '<li><a href="{}">{}</a></li>',
                reverse('admin:Invoice_project_change', args=(project.id,)),
                f'{project.title}',
            )
        projects += '</ul>'
        return mark_safe(projects)

    get_projects.short_description = _('PROJECTS')

    def get_fees(self, invoice):
        projects = '<ul class="field_ul_table">'
        for project in invoice.project_set.all():
            fees = '<ul class="field_ul_table">'
            for fee in project.fee_set.all():
                fees += format_html(
                    '<li><a href="{}">{}</a></li>',
                    reverse('admin:Invoice_fee_change', args=(fee.id,)),
                    f'{fee.description}',
                )
            projects += fees + '</ul><hr style="color: black">'
        projects += '</ul>'
        return mark_safe(projects)

    get_fees.short_description = _('Fees')


class InvoicerOfProjectFilter(SimpleListFilter):
    title = _('INVOICER')
    parameter_name = 'InvoicerIS'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicer.id, invoicer.name)
                for invoicer in Invoicer.objects.all().order_by('name')
            ]
        return [
            (invoicer.id, invoicer.name)
            for invoicer in Invoicer.objects.filter(
                manager=request.user
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice__in=Invoice.objects.filter(
                    invoicee__in=Invoicee.objects.filter(invoicer=self.value())
                )
            )


class InvoiceeOfProjectFilter(SimpleListFilter):
    title = _('INVOICEE')
    parameter_name = 'InvoiceeIS'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicee.id, invoicee.name)
                for invoicee in Invoicee.objects.all().order_by('name')
            ]
        return [
            (invoicee.id, invoicee.name)
            for invoicee in Invoicee.objects.filter(
                invoicer__in=Invoicer.objects.filter(
                    manager=request.user
                )
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice__in=Invoice.objects.filter(invoicee=self.value())
            )


@register(Project)
class ProjectAdmin(ModelAdmin):

    list_per_page = 25
    list_filter = [InvoicerOfProjectFilter, InvoiceeOfProjectFilter]
    search_fields = ('title',)
    list_display = (
        'title',
        'get_invoice',
        'get_fees',
    )
    autocomplete_fields = ('invoice',)
    inlines = [FeeStackedInline,]

    def get_invoice(self, project):
        invoice = format_html(
            '<a href="{}">{}</a>',
            reverse('admin:Invoice_invoice_change', args=(project.id,)),
            f'{project.invoice}',
        )
        return invoice

    get_invoice.short_description = _('INVOICE')

    def get_fees(self, project):
        fees = mark_safe('<ul class="field_ul_table">')
        for fee in project.fee_set.all():
            fees += format_html(
                '<li><a href="{}">{}</a></li>',
                reverse('admin:Invoice_project_change', args=(fee.id,)),
                f'{fee.description}',
            )
        return fees + mark_safe('</ul>')

    get_fees.short_description = _('Fees')

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            invoice__in=Invoice.objects.all().filter(
                invoicer__in=Invoicer.objects.filter(manager=request.user),
            )
        ).order_by('-id')

    # def delete_model(self, request, project):
    #     project.delete()

    # def delete_query(self, request, projects):
    #     for project in projects:
    #         project.delete()

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.invoice.invoicer.manager == request.user
            )
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.invoice.invoicer.manager == request.user
                and not obj.invoice.paymentInvoice.exists()
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.invoice.invoicer.manager == request.user
                and not obj.invoice.paymentInvoice.exists()
            )
        return True


class InvoicerOfProjectItemsFilter(SimpleListFilter):
    title = _('Invoicer')
    parameter_name = 'InvoicerIS'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicer.id, invoicer.name)
                for invoicer in Invoicer.objects.all().order_by('name')
            ]
        return [
            (invoicer.id, invoicer.name)
            for invoicer in Invoicer.objects.filter(
                manager=request.user
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                project__in=Project.objects.filter(
                    invoice__in=Invoice.objects.filter(
                        invoicee__in=Invoicee.objects.filter(
                            invoicer=self.value()
                        )
                    )
                )
            )


class InvoiceeOfProjectItemsFilter(SimpleListFilter):
    title = _('Invoicee')
    parameter_name = 'InvoiceeIS'

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicee.id, invoicee.name)
                for invoicee in Invoicee.objects.all().order_by('name')
            ]
        return [
            (invoicee.id, invoicee.name)
            for invoicee in Invoicee.objects.filter(
                invoicer__in=Invoicer.objects.filter(manager=request.user)
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                project__in=Project.objects.filter(
                    invoice__in=Invoice.objects.filter(invoicee=self.value())
                )
            )


@register(Fee)
class FeeAdmin(ModelAdmin):

    list_per_page = 25
    list_filter = (
        InvoicerOfProjectItemsFilter,
        InvoiceeOfProjectItemsFilter,
    )
    list_display = (
        'description',
        'get_project',
        'get_beforeVAT',
        'get_afterVAT',
    )
    search_fields = ('description',)
    autocomplete_fields = ('project',)

    def get_project(self, fee):
        project = '<ul class="field_ul_table">'
        project += format_html(
            '<a href="{}">{}</a>',
            reverse('admin:Invoice_project_change', args=(fee.project.id,)),
            f'{fee.project.title}',
        )
        return mark_safe(project)

    get_project.short_description = _('PROJECT')

    def get_afterVAT(self, fee):
        return f'{round(fee.rateUnit * fee.count * Decimal(1 + fee.vat / 100), 2)}{get_currency_symbol(fee.project.invoice.baseCurrency)}'

    get_afterVAT.short_description = _('AfterVAT')

    def get_beforeVAT(self, fee):
        return f'{round(fee.rateUnit * fee.count, 2)}{get_currency_symbol(fee.project.invoice.baseCurrency)}'

    get_beforeVAT.short_description = _('BeforeVAT')

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request)
        if not request.user.is_superuser:
            fields.remove('bookKeepingAmount')
        return fields

    # def delete_model(self, request, fee):
    #     fee.delete()

    # def delete_queryset(self, request, fees):
    #     for fee in fees:
    #         invoice = fee.project.invoice
    #         print(invoice.owedAmount)
    #         invoice.owedAmount -= fee.rateUnit * fee.count * Decimal(
    #             round(1 + fee.vat / 100, 2)
    #         )
    #         print(invoice.owedAmount)
    #         invoice.save()
    #         fee.delete()

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            project__in=Project.objects.all().filter(
                invoice__in=Invoice.objects.all().filter(
                    invoicer__in=Invoicer.objects.filter(manager=request.user),
                )
            )
        )

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.project.invoice.invoicer.manager == request.user
            )
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.project.invoice.invoicer.manager == request.user
                and not obj.project.invoice.paymentInvoice.exists()
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.project.invoice.invoicer.manager == request.user
                and not obj.project.invoice.paymentInvoice.exists()
            )
        return True


class PaymentInvoiceeFilter(SimpleListFilter):
    title = _('INVOICEE')
    parameter_name = _('INVOICEE')

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return [
                (invoicee.id, invoicee.name)
                for invoicee in Invoicee.objects.all().order_by('name')
            ]
        return [
            (invoicee.id, invoicee.name)
            for invoicee in Invoicee.objects.filter(
                invoicer__in=Invoicer.objects.filter(
                    manager=request.user
                )
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice__in=Invoice.objects.filter(
                    invoicee=self.value()
                )
            )


class PaymentInvoicerFilter(SimpleListFilter):

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
            for invoicer in Invoicer.objects.filter(
                manager=request.user
            ).order_by('name')
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice__in=Invoice.objects.filter(
                    invoicer=self.value()
                )
            )


@register(Payment)
class PaymentAdmin(ModelAdmin):

    list_per_page = 25
    list_filter = (
        'paymentMethod',
        PaymentInvoicerFilter,
        PaymentInvoiceeFilter,
    )
    list_display = (
        'paidAmount',
        'get_invoice',
    )
    autocomplete_fields = ('payor',)

    def get_form(self, request, obj=None, **kwargs):
        form = super(PaymentAdmin, self).get_form(request, obj, **kwargs)
        invoices = form.base_fields['invoice'].queryset
        if request.user.is_superuser:
            form.base_fields['invoice'].queryset = invoices.filter(
                paidAmount__lt=F('owedAmount')
            ).order_by('-id')
        else:
            form.base_fields['invoice'].queryset = invoices.filter(
                paidAmount__lt=F('owedAmount')
            ).filter(
                invoicer__in=Invoicer.objects.filter(manager=request.user)
            ).order_by('-id')
        return form

    def get_invoice(self, payment):
        invoices = '<ul class="field_ul_table">'
        for invoice in payment.invoice.all():
            invoices += format_html(
                '<li><a href="{}">{}</a></li>',
                reverse('admin:Invoice_invoice_change', args=(invoice.id,)),
                f'{invoice}',
            )
        invoices += '</ul>'
        return mark_safe(invoices)

    get_invoice.short_description = _('INVOICE')

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            invoice__in=Invoice.objects.all().filter(
                invoicer__in=Invoicer.objects.filter(manager=request.user),
            )
        )

    # def delete_model(self, request, payment):
    #     payment.delete()

    # def delete_queryset(self, request, payments):
    #     for payment in payments:
    #         coverage = round(payment.paidAmount / payment.invoice.count(), 2)
    #         for invoice in payment.invoice.all():
    #             invoice.paidAmount -= coverage
    #             invoice.save()
    #         payment.delete()

    def save_model(self, request, payment, form, change):
        payment.save()

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            return (
                request.user.is_superuser
                or obj.invoice.filter(
                    invoicer__in=Invoicer.objects.filter(manager=request.user)
                ).exists()
            )
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return (
                request.user.is_superuser
                or obj.invoice.filter(
                    invoicer__in=Invoicer.objects.filter(manager=request.user)
                ).exists()
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return (
                request.user.is_superuser
                or obj.invoice.filter(
                    invoicer__in=Invoicer.objects.filter(manager=request.user)
                ).exists()
            )
        return True
