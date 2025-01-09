from datetime import date
from decimal import Decimal
from os import remove, getcwd
from os.path import join

from django.contrib.messages import error, success
from django.shortcuts import render
from django.db.models import F, Exists, OuterRef
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
    CreateView,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

from Core.forms import InvoiceFilterControlForm, PaymentFilterControlForm

from Invoicer.models import Invoicer, BankAccount
from Invoicee.models import Invoicee
from Core.utils import HTTPResponseHXRedirect
from .models import Invoice, Project, Fee, Payment
from .forms import ProjectForm, FeeForm, InvoiceForm, PaymentForm
from .utils import (
    create_credit_note,
    generate_invoice_file,
    processInvoiceDraftDataAndSave,
    LateXError,
)
from InvoiceGenerator.settings import TEMPTEXFILESDIR


@login_required
def download_invoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    try:
        file = generate_invoice_file(invoice)
        pathToFile = join(getcwd(), TEMPTEXFILESDIR, file)
        response = FileResponse(
            open(pathToFile, 'rb'),
            content_type='application/pdf',
            filename=file,
        )
        return response
    except LateXError as e:
        error(request, ' '.join(e.args))
        return None


class BaseInvoiceListView(ListView, LoginRequiredMixin):

    queryset = Invoice.objects.select_related('invoicer', 'invoicee')
    template_name = './Invoice-index.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_invoice_changelist')
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoicee_invoice_changelist')
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoice-index-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.GET:
            invoiceFilterControlForm = InvoiceFilterControlForm(
                initial={
                    'beginDate': self.request.GET['beginDate'],
                    'endDate': self.request.GET['endDate'],
                }
            )
        else:
            invoiceFilterControlForm = InvoiceFilterControlForm()
        managerHasMultipleInvoicers = Invoicer.objects.filter(
            manager=self.request.user
        ).count() > 1
        context.update({
            'form': invoiceFilterControlForm,
            'managerHasMultipleInvoicers': managerHasMultipleInvoicers,
        })
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if self.request.GET:
            return queryset.filter(
                facturationDate__gte=self.request.GET['beginDate']
            ).filter(
                facturationDate__lte=self.request.GET['endDate']
            ).filter(
                invoicer=Invoicer.objects.get(manager=self.request.user)
            )
        return queryset.filter(
            facturationDate__gte=f'{date.today().year}-01-01'
        ).filter(
            facturationDate__lte=f'{date.today().year}-12-31'
        ).filter(
            invoicer=Invoicer.objects.get(manager=self.request.user)
        )


class InvoiceListView(BaseInvoiceListView):

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs).filter(
            state__in=[0, 2, 3]
        )
        return queryset


class CreditNoteListView(BaseInvoiceListView):

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs).filter(state=4)
        return queryset


class EstimateListView(BaseInvoiceListView):

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs).filter(state=1)
        return queryset


class InvoiceDetailView(DetailView, LoginRequiredMixin):
    model = Invoice
    template_name = 'Invoice-detail.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_invoice_change'),
                    args=[self.object.id],
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoice_invoice_change'),
                    args=[self.object.id],
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './invoice-detail-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )


@login_required()
def add_estimate(request):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_add')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoicee_invoice_add')
            )
    invoiceForm = InvoiceForm()
    invoicer = Invoicer.objects.get(manager=request.user)
    invoiceForm.fields['bankAccount'].queryset = invoicer.bankAccounts
    invoiceForm.fields['bankAccount'].empty_label = _('NoBankAccount')
    invoiceForm.fields['invoicee'].queryset = invoicer.invoicee_set.all()
    invoiceForm.fields.pop('facturationDate')
    invoiceForm.fields.pop('dueDate')
    if request.method == 'POST':
        invoiceData = {
            'invoicer': invoicer,
            'invoicee': Invoicee.objects.get(
                id=int(request.POST.get('invoicee'))
            ),
            'baseCurrency': request.POST.get('baseCurrency'),
            'paymentMethod': request.POST.get('paymentMethod'),
        }
        invoiceID = processInvoiceDraftDataAndSave(invoiceData, estimate=True)
        return HttpResponseRedirect(
            reverse('Invoice:modify', args=[invoiceID]),
        )
    context = {'invoiceForm': invoiceForm, 'estimate': True}
    if request.META.get('HTTP_HX_REQUEST'):
        context.update({'dialogForm': True})
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


@login_required()
def add_estimate_for(request, invoicee):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_add')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoicee_invoice_add')
            )
    invoiceForm = InvoiceForm()
    invoicer = Invoicer.objects.get(manager=request.user)
    invoicee = Invoicee.objects.get(id=invoicee)
    invoiceForm.fields['bankAccount'].queryset = invoicer.bankAccounts
    invoiceForm.fields['bankAccount'].empty_label = _('NoBankAccount')
    invoiceForm.fields.pop('invoicee')
    invoiceForm.fields.pop('facturationDate')
    invoiceForm.fields.pop('dueDate')
    if request.method == 'POST':
        invoiceData = {
            'invoicer': invoicer,
            'invoicee': invoicee,
            'baseCurrency': request.POST.get('baseCurrency'),
            'paymentMethod': request.POST.get('paymentMethod'),
        }
        invoiceID = processInvoiceDraftDataAndSave(invoiceData, estimate=True)
        return HttpResponseRedirect(
            reverse('Invoice:modify', args=[invoiceID]),
        )
    context = {
        'invoiceForm': invoiceForm,
        'invoicee': invoicee,
        'dialogForm': True,
        'estimate': True,
    }
    if request.META.get('HTTP_HX_REQUEST'):
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


@login_required()
def add_invoice_for(request, invoicee):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_add')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoicee_invoice_add')
            )
    invoicer = Invoicer.objects.get(manager=request.user)
    invoicee = Invoicee.objects.get(id=invoicee)
    invoiceForm = InvoiceForm()
    bankAccounts = invoicer.bankAccounts
    invoiceForm.fields['bankAccount'].queryset = bankAccounts
    invoiceForm.fields['bankAccount'].empty_label = _('NoBankAccount')
    invoiceForm.fields.pop('invoicee')
    if request.method == 'POST':
        bankAccount = bankAccounts.get(
            id=int(request.POST.get('bankAccount'))
        ) if request.POST.get('bankAccount') else None
        invoiceData = {
            'invoicer': invoicer,
            'invoicee': invoicee,
            'bankAccount': bankAccount,
            'facturationDate': request.POST.get('facturationDate'),
            'dueDate': request.POST.get('dueDate'),
            'baseCurrency': request.POST.get('baseCurrency'),
            'paymentMethod': request.POST.get('paymentMethod'),
        }
        invoiceID = processInvoiceDraftDataAndSave(invoiceData, estimate=False)
        return HttpResponseRedirect(
            reverse('Invoice:modify', args=[invoiceID]),
        )
    context = {
        'invoiceForm': invoiceForm,
        'invoicee': invoicee,
        'dialogForm': True,
        'invoice': True,
    }
    if request.META.get('HTTP_HX_REQUEST'):
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


@login_required()
def add_invoice(request):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_add')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoicee_invoice_add')
            )
    invoiceForm = InvoiceForm()
    invoicer = Invoicer.objects.get(manager=request.user)
    invoiceForm.fields['bankAccount'].queryset = invoicer.bankAccounts
    invoiceForm.fields['bankAccount'].empty_label = _('NoBankAccount')
    invoiceForm.fields['invoicee'].queryset = invoicer.invoicee_set.all()
    if request.method == 'POST':
        bankAccount = invoicer.bankAccounts.get(
            id=int(request.POST.get('bankAccount'))
        ) if request.POST.get('bankAccount') else None
        invoiceData = {
            'invoicer': invoicer,
            'invoicee': Invoicee.objects.get(
                id=int(request.POST.get('invoicee'))
            ),
            'bankAccount': bankAccount,
            'facturationDate': request.POST.get('facturationDate'),
            'dueDate': request.POST.get('dueDate'),
            'baseCurrency': request.POST.get('baseCurrency'),
            'paymentMethod': request.POST.get('paymentMethod'),
        }
        invoiceID = processInvoiceDraftDataAndSave(invoiceData, estimate=False)
        return HttpResponseRedirect(
            reverse('Invoice:modify', args=[invoiceID]),
        )
    context = {'invoiceForm': invoiceForm, 'invoice': True}
    if request.META.get('HTTP_HX_REQUEST'):
        context.update({'dialogForm': True})
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


@login_required()
def delete_invoice(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_delete', args=[invoice])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_invoice_delete', args=[invoice])
            )
    invoice = Invoice.objects.get(id=invoice)
    if invoice.state != 0 and invoice.state != 1:
        return render(request, 'errorPages/405.html', status=405)
    invoice.delete()
    success(request, _('InvoiceSuccessfullyDeleted'))
    return HttpResponseRedirect(reverse('Invoice:index'))


@login_required()
def create_creditNoteOfInvoice(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_changelist')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_invoice_changelist')
            )
    invoice = Invoice.objects.get(id=invoice)
    if invoice.state == 0:
        return render(request, 'errorPages/405.html', status=405)
    success(request, _('CreditNoteSuccessfullyCreated'))
    create_credit_note(invoice)
    return HttpResponseRedirect(reverse('Invoice:index'))


@require_GET
@login_required()
def validate_invoice(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_changelist')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_invoice_changelist')
            )
    invoice = Invoice.objects.get(id=invoice)
    if invoice.project_set.count() == 0:
        error(request, _('InvoiceHasNoProjects'))
    for project in invoice.project_set.all():
        if project.fee_set.count() == 0:
            error(request, _('Project %(p)s has no fees', {'p': project}))
    invoice.state = 2
    invoice.save()
    success(request, _('InvoiceSuccessfullyValidated'))
    return render(request, 'Invoice-list-item.html', {'invoice': invoice})


@login_required()
def modify_invoice(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_invoice_change', args=[invoice])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_invoice_change', args=[invoice])
            )
    invoice = Invoice.objects.get(id=invoice)
    invoicer = invoice.invoicer
    projectForm = ProjectForm()
    feeForm = FeeForm()
    projectSet = []
    for project in Project.objects.filter(invoice=invoice):
        feeSet = []
        for fee in project.fee_set.all():
            feeSet.append({
                'instance': fee,
                'form': FeeForm(instance=fee),
            })
        projectSet.append({
            'instance': project,
            'form': ProjectForm(instance=project),
            'feeSet': feeSet,

        })
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoice.invoicer = Invoicer.objects.get(
                id=request.POST.get('invoicer')
            )
        invoice.invoicee = Invoicee.objects.get(
            id=request.POST.get('invoicee')
        )
        if request.POST.get('bankAccount'):
            invoice.bankAccount = BankAccount.objects.get(
                id=request.POST.get('bankAccount')
            )
        invoice.paymentMethod = request.POST.get('paymentMethod')
        invoice.baseCurrency = request.POST.get('baseCurrency')
        invoice.dueDate = request.POST.get('dueDate')
        invoice.facturationDate = request.POST.get('facturationDate')
        invoice.save()
        success(request, _('InvoiceSuccessfullyModified'))
    invoiceForm = InvoiceForm(instance=invoice)
    bankAccounts = invoicer.bankAccounts
    invoiceForm.fields['bankAccount'].empty_label = _('NoBankAccount')
    invoiceForm.fields['bankAccount'].queryset = invoicer.bankAccounts
    if invoice.state == 1:
        invoiceForm.fields.pop('facturationDate')
        invoiceForm.fields.pop('dueDate')
        invoiceForm.fields.pop('paymentMethod')
    invoiceForm.fields['invoicee'].queryset = invoicer.invoicee_set.all()
    context = {
        'invoice': invoice,
        'invoiceForm': invoiceForm,
        'projectSet': projectSet,
        'projectForm': projectForm,
        'feeForm': feeForm,
    }
    if request.META.get('HTTP_HX_REQUEST'):
        return render(request, './Invoice-modify-partial.html', context)
    else:
        return render(request, './invoice-modify.html', context)


@require_POST
@login_required()
def modify_project(request, project):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_project_change', args=[project])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_project_change', args=[project])
            )
    project = Project.objects.get(id=project)
    project.title = request.POST['title']
    project.save()
    success(request, _('ProjectSuccessfullyModified'))
    return HTTPResponseHXRedirect(
        reverse('Invoice:modify', args=[project.invoice.id])
    )


@require_http_methods(['GET', 'POST'])
@login_required()
def modify_fee(request, fee):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_fee_change', args=[fee])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_fee_change', args=[fee])
            )
    fee = Fee.objects.get(id=fee)
    if request.method == 'GET':
        feeForm = FeeForm(instance=fee)
        context = {'feeForm': feeForm, 'fee': fee}
        return render(request, './Fee-form.html', context)
    elif request.method == 'POST':
        fee.description = request.POST.getlist('description')[0]
        fee.rateUnit = Decimal(request.POST.getlist('rateUnit')[0])
        fee.vat = Decimal(request.POST.getlist('vat')[0])
        fee.count = int(request.POST.getlist('count')[0])
        fee.save()
        success(request, _('ProjectAndIncludedFeesSuccessfullyModified'))
        return HTTPResponseHXRedirect(
            reverse('Invoice:modify', args=[fee.project.invoice.id])
        )


@require_POST
@login_required()
def add_projectAndFeesToInvoice(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_project_add')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_project_add')
            )
    invoice = Invoice.objects.get(id=invoice)
    project = Project()
    project.title = request.POST['title']
    project.invoice = invoice
    project.save()
    if len(request.POST.getlist('description')) > 1:
        for i, description in enumerate(request.POST.getlist('description')):
            fee = Fee()
            fee.project = project
            fee.description = description
            fee.rateUnit = request.POST.getlist('rateUnit')[i]
            fee.count = request.POST.getlist('count')[i]
            fee.vat = request.POST.getlist('vat')[i]
            fee.save()
    else:
        fee = Fee()
        fee.project = project
        fee.description = request.POST['description']
        fee.rateUnit = request.POST['rateUnit']
        fee.count = request.POST['count']
        fee.vat = request.POST['vat']
        fee.save()
    success(request, _('ProjectAndIncludedFeesSuccessfullyAdded'))
    return HTTPResponseHXRedirect(
        reverse('Invoice:modify', args=[project.invoice.id])
    )


@require_POST
@login_required()
def add_feesToProject(request, project):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_project_change', args=[project])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_project_change', args=[project])
            )
    project = Project.objects.get(id=project)
    if len(request.POST.getlist('description')) > 1:
        for i, description in enumerate(request.POST.getlist('description')):
            fee = Fee()
            fee.project = project
            fee.description = description
            fee.rateUnit = request.POST.getlist('rateUnit')[i]
            fee.count = request.POST.getlist('count')[i]
            fee.vat = request.POST.getlist('vat')[i]
            fee.save()
    else:
        fee = Fee()
        fee.project = project
        fee.description = request.POST['description']
        fee.rateUnit = request.POST['rateUnit']
        fee.count = request.POST['count']
        fee.vat = request.POST['vat']
        fee.save()
    success(request, _('FeeSuccessfullyAdded'))
    return HTTPResponseHXRedirect(
        reverse('Invoice:modify', args=[project.invoice.id])
    )


@require_GET
@login_required()
def invoice_estimate(request, invoice):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_project_changelist')
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_project_changelist')
            )
    invoice = Invoice.objects.get(id=invoice)
    invoice.state = 2
    invoice.save()
    success(request, _('EstimateSuccessfullyInvoiced'))
    return render(request, './Invoice-list-item.html', {'invoice': invoice})


@require_http_methods(['DELETE'])
@login_required()
def delete_fee(request, fee):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_fee_delete', args=[fee])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_fee_delete', args=[fee])
            )
    fee = Fee.objects.get(id=fee)
    if fee.project.fee_set.count() > 1:
        fee.delete()
    else:
        error(request, _('ProjectsMustHaveAtLeastOneFee'))
        response = HTTPResponseHXRedirect(
            reverse('Invoice:modify', args=[fee.project.invoice.id])
        )
        response['HX-Redirect'] = response['Location']
        response.status_code = 405
        return response
    success(request, _('FeeSuccessfullyDeleted'))
    return HTTPResponseHXRedirect(
        reverse('Invoice:modify', args=[fee.project.invoice.id])
    )


@require_http_methods(['DELETE'])
@login_required()
def delete_project(request, project):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_project_delete', args=[project])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_project_delete', args=[project])
            )
    project = Project.objects.get(id=project)
    if project.invoice.project_set.count() > 1:
        project.delete()
    else:
        error(request, _('InvoicesMustHaveAtLeastOneProject'))
        response = HTTPResponseHXRedirect(
            reverse('Invoice:modify', args=[project.invoice.id])
        )
        response['HX-Redirect'] = response['Location']
        response.status_code = 405
        return response
    success(request, _('ProjectSuccessfullyDeleted'))
    return HTTPResponseHXRedirect(
        reverse('Invoice:modify', args=[project.invoice.id])
    )


@require_http_methods(['DELETE'])
@login_required()
def delete_payment(request, payment):
    if request.user.is_superuser:
        if request.META.get('HTTP_HX_REQUEST'):
            return HTTPResponseHXRedirect(
                reverse_lazy('admin:Invoice_payment_delete', args=[payment])
            )
        else:
            return HttpResponseRedirect(
                reverse_lazy('admin:Invoice_payment_delete', args=[payment])
            )
    payment = Payment.objects.get(id=payment)
    payment.delete()
    success(request, _('PaymentSuccessfullyDeleted'))
    return HTTPResponseHXRedirect(reverse('Invoice:payments'))


class PaymentCreateView(CreateView, LoginRequiredMixin):

    model = Payment
    form_class = PaymentForm
    template_name = './Payment-form.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_payment_add'),
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoice_payment_add'),
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            context.update({'dialogForm': True})
            return render(
                self.request,
                './Payment-form-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'update': False})
        return context

    def get_form(self):
        paymentForm = super().get_form()
        invoicer = Invoicer.objects.get(manager=self.request.user)
        outStandingInvoicesOfInvoicer = Invoice.objects.select_related(
            'invoicer', 'invoicee'
        ).filter(
            invoicer=invoicer
        ).filter(
            state__in=[0, 2]
        ).filter(
            owedAmount__gt=F('paidAmount')
        )
        paymentForm.fields['payor'].queryset = paymentForm.fields[
            'payor'
        ].queryset.filter(
            Exists(
                outStandingInvoicesOfInvoicer.filter(invoicee=OuterRef('id'))
            )
        )
        paymentForm.fields['invoice'].queryset = outStandingInvoicesOfInvoicer
        paymentForm.fields['bankAccount'].queryset = invoicer.bankAccounts
        paymentForm.fields['bankAccount'].empty_label = _('NoBankAccount')
        return paymentForm

    def form_invalid(self, form):
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#payment-form-dialog'
        return response

    def form_valid(self, form):
        form.instance.invoicee = Invoicee.objects.get(
            id=self.request.POST['payor']
        )
        form.instance.paymentDay = self.request.POST['paymentDay']
        form.instance.paymentMethod = self.request.POST['paymentMethod']
        form.instance.paidAmount = Decimal(self.request.POST['paidAmount'])
        form.instance.paidInvoices = Invoice.objects.filter(
            id__in=self.request.POST['invoice']
        )
        response = super().form_valid(form)
        return response


class PaymentUpdateView(UpdateView, LoginRequiredMixin):

    model = Payment
    form_class = PaymentForm
    template_name = './Payment-form.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_payment_change'),
                    args=[self.object.id],
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoice_payment_change'),
                    args=[self.object.id],
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            context.update({'dialogForm': True})
            return render(
                self.request,
                './Payment-form-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'update': True})
        return context

    def get_form(self):
        paymentForm = super().get_form()
        invoicer = Invoicer.objects.get(manager=self.request.user)
        paymentForm.fields['bankAccount'].queryset = invoicer.bankAccounts
        paymentForm.fields['bankAccount'].empty_label = _('NoBankAccount')
        outStandingInvoicesOfInvoicer = Invoice.objects.filter(
            invoicer=invoicer
        ).filter(
            owedAmount__gt=F('paidAmount')
        )
        paymentForm.fields['payor'].queryset = Invoicee.objects.filter(
            Exists(
                outStandingInvoicesOfInvoicer.filter(invoicee=OuterRef('id'))
            )
        )

    def form_invalid(self, form):
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#payment-form-dialog'
        return response

    def form_valid(self, form):
        form.instance.invoicee = Invoicee.objects.get(
            id=self.request.POST['payor']
        )
        form.instance.paymentDay = self.request.POST['paymentDay']
        form.instance.paymentMethod = self.request.POST['paymentMethod']
        form.instance.paidAmount = Decimal(self.request.POST['paidAmount'])
        form.instance.paidInvoices = Invoice.objects.filter(
            id__in=self.request.POST['invoice']
        )
        response = super().form_valid(form)
        return response


class PaymentListView(ListView, LoginRequiredMixin):

    model = Payment
    queryset = Payment.objects.select_related(
        'invoice', 'payor', 'bankAccount')
    template_name = './Payment-index.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_payment_changelist'),
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoice_payment_changelist'),
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Payment-index-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.GET:
            success(self.request, _('ResultsSuccesfullyFiltered'))
            context.update({
                'searchForm': PaymentFilterControlForm(
                    initial={
                        'payor': self.request.GET['payor'],
                        'beginDate': self.request.GET['beginDate'],
                        'endDate': self.request.GET['endDate'],
                    }
                ),
                'payment_list': Payment.objects.filter(
                    paymentDay__gte=self.request.GET['beginDate']
                ).filter(
                    paymentDay__lte=self.request.GET['endDate']
                ).select_related(
                    'payor'
                ).filter(
                    payor__in=Invoicee.objects.select_related(
                        'invoicer'
                    ).filter(
                        invoicer=Invoicer.objects.get(
                            manager=self.request.user
                        )
                    )
                ).filter(
                    payor__name__icontains=self.request.GET['payor']
                ),
            })
        else:
            context.update({
                'searchForm': PaymentFilterControlForm(
                    initial={
                        'beginDate': f'01-01-{date.today().year}',
                        'endDate': f'31-12-{date.today().year}',
                    }
                ),
                'payment_list': Payment.objects.select_related(
                    'payor'
                ).filter(
                    payor__in=Invoicee.objects.select_related(
                        'invoicer'
                    ).filter(
                        invoicer=Invoicer.objects.get(
                            manager=self.request.user
                        )
                    )
                ).filter(
                    paymentDay__gte=f'{date.today().year}-01-01'
                ).filter(
                    paymentDay__lte=f'{date.today().year}-12-31'
                ),
            })
        if not context['payment_list']:
            error(
                self.request,
                _('UserHasNoPaymentsOrNoPaymentFoundWithTheChosenFilter'),
            )
        return context


class PaymentDetailView(DetailView, LoginRequiredMixin):

    model = Payment
    template_name = './Invoice-index.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.is_superuser:
            if self.request.META.get('HTTP_HX_REQUEST'):
                return HTTPResponseHXRedirect(
                    reverse_lazy('admin:Invoice_payment_change'),
                    args=[self.object.id],
                )
            else:
                return HttpResponseRedirect(
                    reverse_lazy('admin:Invoice_payment_changelist'),
                    args=[self.object.id],
                )
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoice-index-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        payment = context['payment']
        if self.request.GET:
            context.update({
                'payment': payment,
                'invoice_list': payment.invoice.filter(
                    facturationDate__gte=self.request.GET['beginDate']
                ).filter(
                    facturationDate__lte=self.request.GET['endDate']
                ),
                'form': InvoiceFilterControlForm(
                    initial={
                        'beginDate': self.request.GET['beginDate'],
                        'endDate': self.request.GET['endDate'],
                    }
                ),
            })
        else:
            context.update({
                'payment': payment,
                'invoice_list': payment.invoice.all(),
                'form': InvoiceFilterControlForm(
                    initial={
                        'beginDate': _('dd-mm-yyyy'),
                        'endDate': _('dd-mm-yyyy'),
                    }
                ),
            })
        return context
