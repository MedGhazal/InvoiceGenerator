from datetime import date, timedelta
from csv import DictWriter
from os import getcwd, remove
from os.path import join
from tempfile import (
    SpooledTemporaryFile,
)
from zipfile import (
    ZIP_DEFLATED,
    ZipFile,
)
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django.contrib.admin import (
    action,
    register,
    ModelAdmin,
    SimpleListFilter,
)
from django.http import (
    HttpResponse,
)
from django.contrib.messages import error, warning
from rangefilter.filters import DateRangeFilter
from Invoicee.models import Invoicee
from Invoicer.models import Invoicer
from .models import Invoice, Project, Fee, Payment
from .utils import (
    generate_invoice_file,
    export_invoice_data,
    LateXError,
)
from InvoiceGenerator.settings import TEMPTEXFILESDIR, EXPORT_DATA_HEADER


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
        invoice.draft = False
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
            )
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
                for invoicer in Invoicer.objects.all()
            ]
        return [
            (invoicer.id, invoicer.name)
            for invoicer in Invoicer.objects.filter(manager=request.user)
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(invoicer=self.value())


@register(Invoice)
class InvoiceAdmin(ModelAdmin):
    actions = [
        generate_invoice,
        export_invoices,
        validate_invoices,
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
        'dueDate',
        'facturationDate',
        'get_status',
        'get_balance',
    )
    autocomplete_fields = ('invoicee',)
    search_fields = ('description',)

    def save_model(self, request, obj, form, change):
        if form.cleaned_data['draft'] != form.initial['draft']:
            invoices = Invoice.objects.filter(
                draft=form.cleaned_data['draft']
            )
            if invoices.count() > 0:
                obj.count = max(
                    invoice.count for invoice in invoices
                ) + 1
            else:
                obj.count = 1
        obj.save()

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user),
        )

    def has_view_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoicer.manager != request.user
        ):
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None:
            return (
                obj.invoicer.manager == request.user
                and obj.paidAmount < obj.owedAmount
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None:
            return (
                obj.invoicer.manager == request.user
                and obj.draft
                and obj.paidAmount == 0
            )
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser and db_field.name == 'invoicer':
            kwargs['queryset'] = Invoicer.objects.filter(manager=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request)
        fields.remove('owedAmount')
        fields.remove('paidAmount')
        if not request.user.is_superuser:
            fields.remove('count')
            fields.remove('salesAccount')
            fields.remove('vatAccount')
        return fields

    def get_status(self, invoice):
        if invoice.status == 0:
            return mark_safe('&#128998;')
        elif invoice.status == 1:
            return mark_safe('&#129003;')
        elif invoice.status == 2:
            return mark_safe('&#129001;')
        elif invoice.status == 3:
            days = date.today() - invoice.dueDate
            if days.days == 0:
                return mark_safe('&#129000;')
            if days.days == 1:
                return mark_safe('&#12900;')
            if days.days > 30:
                return mark_safe('&#128997;')
            return mark_safe('&#128999;')

    get_status.short_description = _('Status')

    def get_balance(self, invoice):
        if invoice.draft:
            return _('IsDraft')
        balance = invoice.owedAmount - invoice.paidAmount
        if balance == 0:
            return '-'
        elif invoice.invoicee.country.lower() == 'mar':
            return f'{balance}DH'
        elif invoice.invoicee.country.lower() == 'fr':
            return f'{balance}€'
        return None

    get_balance.short_description = _('TBPaid')

    def get_projects(self, invoice):
        projects = []
        for project in invoice.project_set.all():
            projects.append(str(project))
        return f'{projects}'

    get_projects.short_description = _('PROJECTS')


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
            for invoicer in Invoicer.objects.filter(manager=request.user)
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
            )
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice__in=Invoice.objects.filter(invoicee=self.value())
            )


@register(Project)
class ProjectAdmin(ModelAdmin):
    list_filter = [InvoicerOfProjectFilter, InvoiceeOfProjectFilter]
    search_fields = ('title',)
    list_display = (
        'title',
        'invoice',
    )
    autocomplete_fields = ('invoice',)

    def get_queryset(self, request):
        querySet = super().get_queryset(request)
        if request.user.is_superuser:
            return querySet
        return querySet.filter(
            invoice__in=Invoice.objects.all().filter(
                invoicer__in=Invoicer.objects.filter(manager=request.user),
            )
        )

    def has_view_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoice.invoicer.manager != request.user
        ):
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoice.invoicer.manager != request.user
        ):
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None and (
            not request.user.is_superuser and obj.invoice.invoicer.manager != request.user
        ):
            return False
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
            for invoicer in Invoicer.objects.filter(manager=request.user)
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
            )
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
    list_filter = (
        InvoicerOfProjectItemsFilter,
        InvoiceeOfProjectItemsFilter,
    )
    list_display = (
        'description',
        'project',
    )
    search_fields = ('description',)
    autocomplete_fields = ('project',)

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request)
        if not request.user.is_superuser:
            fields.remove('bookKeepingAmount')
        return fields

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
        if obj is not None and (
            not request.user.is_superuser and obj.project.invoice.invoicer.manager != request.user
        ):
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.project.invoice.invoicer.manager == request.user
                and obj.project.invoice.paidAmount < obj.project.invoice.owedAmount
            )
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return request.user.is_superuser or (
                obj.project.invoice.invoicer.manager == request.user
                and obj.project.invoice.paidAmount < obj.project.invoice.owedAmount
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
            )
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
            for invoicer in Invoicer.objects.filter(manager=request.user)
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
    list_filter = (
        'paymentMethod',
        PaymentInvoicerFilter,
        PaymentInvoiceeFilter,
    )
    list_display = (
        'paidAmount',
        'get_invoice',
    )
    autocomplete_fields = ('invoice',)

    def get_invoice(self, payment):
        return f'{list(str(invoice) for invoice in payment.invoice.all())}'

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

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            if request.user.is_superuser:
                return True
            for invoice in obj.invoice.all():
                return invoice.invoicer.manager == request.user
        return True

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            if request.user.is_superuser:
                return True
            for invoice in obj.invoice.all():
                return invoice.invoicer.manager == request.user
        return True

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            if request.user.is_superuser:
                return True
            for invoice in obj.invoice.all():
                return invoice.invoicer.manager == request.user
        return True

    def has_add_permission(self, request, obj=None):
        if obj is not None:
            if request.user.is_superuser:
                return True
            for invoice in obj.invoice.all():
                return invoice.invoicer.manager == request.user
        return True
