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
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.translation import gettext_lazy as _

from Core.forms import InvoiceFilterControlForm, PaymentFilterControlForm

from Invoicer.models import Invoicer, BankAccount
from Invoicee.models import Invoicee
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
        invoices = context['invoice_list'].filter(
            facturationDate__gte=f'{date.today().year}-01-01'
        ).filter(
            facturationDate__lte=f'{date.today().year}-12-31'
        )
        invoiceFilterControlForm = InvoiceFilterControlForm()
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
            'invoice_list': invoices,
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
            )
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(
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
    invoiceForm = InvoiceForm()
    invoiceForm.fields.pop('facturationDate')
    invoiceForm.fields.pop('dueDate')
    invoiceForm.fields.pop('bankAccount')
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoicer = Invoicer.objects.get(
                id=int(request.POST.get('invoicer'))
            )
        else:
            invoicer = Invoicer.objects.get(manager=request.user)
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
    invoiceForm = InvoiceForm()
    invoicee = Invoicee.objects.get(id=invoicee)
    invoiceForm.fields.pop('invoicee')
    invoiceForm.fields.pop('facturationDate')
    invoiceForm.fields.pop('dueDate')
    invoiceForm.fields.pop('bankAccount')
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoicer = Invoicer.objects.get(
                id=int(request.POST.get('invoicer'))
            )
        else:
            invoicer = Invoicer.objects.get(manager=request.user)
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
    invoicee = Invoicee.objects.get(id=invoicee)
    invoiceForm = InvoiceForm()
    invoiceForm.fields.pop('invoicee')
    invoicer = Invoicer.objects.get(manager=request.user)
    bankAccounts = BankAccount.objects.filter(owner=invoicer)
    if bankAccounts.count() < 2:
        invoiceForm.fields.pop('bankAccount')
    else:
        invoiceForm.fields['bankAccount'].queryset = bankAccounts
    if request.method == 'POST':
        invoicer = Invoicer.objects.get(manager=request.user)
        if bankAccounts.count() > 1:
            bankAccount = bankAccounts.get(
                id=int(request.POST.get('bankAccount'))
            )
        else:
            bankAccount = bankAccounts.first()
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
    invoiceForm = InvoiceForm()
    invoicer = Invoicer.objects.get(manager=request.user)
    bankAccounts = BankAccount.objects.filter(owner=invoicer)
    if bankAccounts.count() < 2:
        invoiceForm.fields.pop('bankAccount')
    else:
        invoiceForm.fields['bankAccount'].queryset = bankAccounts
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoicer = Invoicer.objects.get(
                id=int(request.POST.get('invoicer'))
            )
        else:
            invoicer = Invoicer.objects.get(
                manager=request.user
            )
        if bankAccounts.count() < 2:
            bankAccount = bankAccounts.get(
                id=int(request.POST.get('bankAccount'))
            )
        else:
            bankAccount = bankAccounts.first()
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
    invoice = Invoice.objects.get(id=invoice)
    if invoice.state != 0 and invoice.state != 1:
        return render(request, 'errorPages/405.html', status=405)
    invoice.delete()
    success(request, _('InvoiceSuccessfullyDeleted'))
    return HttpResponseRedirect(reverse('Invoice:index'))


@login_required()
def create_creditNoteOfInvoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    if invoice.state == 0:
        return render(request, 'errorPages/405.html', status=405)
    success(request, _('CreditNoteSuccessfullyCreated'))
    create_credit_note(invoice)
    return HttpResponseRedirect(reverse('Invoice:index'))


@require_POST
@login_required()
def validate_invoice(request, invoice):
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
    invoice = Invoice.objects.get(id=invoice)
    invoicer = Invoicer.objects.get(manager=request.user)
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
    bankAccounts = BankAccount.objects.filter(owner=invoicer)
    if bankAccounts.count() < 2:
        invoiceForm.fields.pop('bankAccount')
    else:
        invoiceForm.fields['bankAccount'].queryset = bankAccounts
    if invoice.state == 1:
        invoiceForm.fields.pop('facturationDate')
        invoiceForm.fields.pop('dueDate')
    invoiceForm.fields['invoicee'].queryset = Invoicee.objects.select_related(
        'invoicer'
    ).filter(
        invoicer=invoicer
    )
    if invoice.state == 1:
        invoiceForm.fields.pop('paymentMethod')
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


@require_POST
@login_required()
def invoice_estimate(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    invoice.state = 2
    return HttpResponse(_('EstimateSuccessfullyInvoiced'))


class HTTPResponseHXRedirect(HttpResponseRedirect):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["HX-Redirect"] = self["Location"]

    status_code = 200


@require_http_methods(['DELETE'])
@login_required()
def delete_fee(request, fee):
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
    payment = Payment.objects.get(id=payment)
    payment.delete()
    success(request, _('PaymentSuccessfullyDeleted'))
    return HTTPResponseHXRedirect(reverse('Invoice:payments'))


class PaymentCreateView(CreateView, LoginRequiredMixin):

    model = Payment
    form_class = PaymentForm
    template_name = './Payment-form.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
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
        paymentForm = context['form']
        invoicer = Invoicer.objects.get(manager=self.request.user)
        if invoicer.bankAccounts.count() < 2:
            paymentForm.fields.pop('bankAccount')
        outStandingInvoicesOfInvoicer = Invoice.objects.select_related(
            'invoicer', 'invoicee'
        ).filter(
            invoicer=invoicer
        ).filter(
            owedAmount__gt=F('paidAmount')
        )
        paymentForm.fields['payor'].queryset = Invoicee.objects.filter(
            Exists(
                outStandingInvoicesOfInvoicer.filter(invoicee=OuterRef('id'))
            )
        )
        paymentForm.fields['invoice'].queryset = outStandingInvoicesOfInvoicer
        if self.request.META.get('HTTP_HX_REQUEST'):
            context.update({
                'form': paymentForm,
                'dialogForm': True,
                'update': False,
            })
        else:
            context.update({'form': paymentForm, 'update': False})
        return context

    def form_valid(self, form):
        form.instance.invoicee = Invoicee.objects.get(
            id=self.request.POST['payor']
        )
        form.instance.paymentDay = self.request.POST['paymentDay']
        form.instance.paymentMethod = self.request.POST['paymentMethod']
        invoicer = Invoicer.objects.get(manager=self.request.user)
        if invoicer.bankAccounts.count() < 2:
            form.instance.bankAccount = invoicer.bankAccounts.fist()
        else:
            form.instance.bankAccount = BankAccount.objects.get(
                id=self.request.POST['bankAccount']
            )
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
        if self.request.META.get('HTTP_HX_REQUEST'):
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
        paymentForm = context['form']
        invoicer = Invoicer.objects.get(manager=self.request.user)
        if invoicer.bankAccounts.count() < 2:
            paymentForm.fields.pop('bankAccount')
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
        paymentForm.fields['invoice'].queryset = outStandingInvoicesOfInvoicer
        if self.request.META.get('HTTP_HX_REQUEST'):
            context.update({
                'form': paymentForm,
                'dialogForm': True,
                'update': True,
            })
        else:
            context.update({'form': paymentForm, 'update': True})
        return context

    def form_valid(self, form):
        form.instance.invoicee = Invoicee.objects.get(
            id=self.request.POST['payor']
        )
        form.instance.paymentDay = self.request.POST['paymentDay']
        form.instance.paymentMethod = self.request.POST['paymentMethod']
        invoicer = Invoicer.objects.get(manager=self.request.user)
        if invoicer.bankAccounts.count() < 2:
            form.instance.bankAccount = invoicer.bankAccounts.fist()
        else:
            form.instance.bankAccount = BankAccount.objects.get(
                id=self.request.POST['bankAccount']
            )
        form.instance.paidAmount = Decimal(self.request.POST['paidAmount'])
        form.instance.paidInvoices = Invoice.objects.filter(
            id__in=self.request.POST['invoice']
        )
        response = super().form_valid(form)
        return response


class PaymentListView(ListView, LoginRequiredMixin):

    model = Payment
    # queryset = Payment.objects.select_related()
    template_name = './Payment-index.html'

    def render_to_response(self, context, **response_kwargs):
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
        invoicer = Invoicer.objects.get(manager=self.request.user)
        if self.request.GET:
            success(self.request, _('ResultsSuccesfullyFiltered'))
            context.update({
                'invoicerHasManyBankAccounts': BankAccount.objects.select_related(
                    'owner'
                ).filter(
                    owner=invoicer
                ).count() > 1,
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
                'invoicerHasManyBankAccounts': BankAccount.objects.select_related(
                    'owner'
                ).filter(
                    owner=invoicer
                ).count() > 1,
                'searchForm': PaymentFilterControlForm(
                    initial={
                        'beginDate': f'01-01-{date.today().year}',
                        'endDate': f'31-12-{date.today().year}',
                    }
                ),
                'payment_list': Payment.objects.select_related(
                    'payor'
                ).filter(
                    payor__in=Invoicee.objects.filter(
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
        invoicer = Invoicer.objects.get(manager=self.request.user)
        payment = context['payment']
        if self.request.GET:
            context.update({
                'invoicerHasManyBankAccounts': BankAccount.objects.select_related(
                    'owner'
                ).filter(
                    owner=invoicer
                ).count() > 1,
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
                'invoicerHasManyBankAccounts': BankAccount.objects.select_related(
                    'owner'
                ).filter(
                    owner=invoicer
                ).count() > 1,
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
