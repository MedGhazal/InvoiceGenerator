from decimal import Decimal
from os import remove, getcwd
from os.path import join

from django.contrib.messages import error, success
from django.shortcuts import render
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _

from Core.forms import InvoiceFilterControlForm

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee
from .models import Invoice, Project, Fee
from .forms import ProjectForm, FeeForm, InvoiceForm
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
        remove(pathToFile)
        return response
    except LateXError as e:
        error(request, ' '.join(e.args))
        return None


class InvoiceListView(ListView, LoginRequiredMixin):
    model = Invoice
    template_name = 'Invoice-index.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './invoice-index-partial.html',
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
        invoiceFilterControlForm = InvoiceFilterControlForm()
        invoicerQuerySet = Invoicer.objects.filter(
            manager=self.request.user
        )
        invoiceFilterControlForm.fields['invoicer'].queryset = invoicerQuerySet
        invoiceFilterControlForm.fields[
            'invoicee'
        ].queryset = Invoicee.objects.filter(invoicer__in=invoicerQuerySet)
        managerHasMultipleInvoicers = Invoicer.objects.filter(
            manager=self.request.user
        ).count() > 1
        if not managerHasMultipleInvoicers:
            invoiceFilterControlForm.fields.pop('invoicer')
        context.update({
            'form': invoiceFilterControlForm,
            'managerHasMultipleInvoicers': managerHasMultipleInvoicers,
        })
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        if self.request.GET:
            print("TEST")
            invoicer = self.request.GET.get('invoicer')
            if not invoicer:
                invoicer = Invoicer.objects.get(manager=self.request.user)
            return queryset.filter(
                invoicer=invoicer
            ).filter(
                invoicee=self.request.GET['invoicee']
            ).filter(
                facturationDate__gte=self.request.GET['beginDate']
            ).filter(
                facturationDate__lte=self.request.GET['endDate']
            )
        return queryset.filter(
            invoicer__in=Invoicer.objects.filter(manager=self.request.user)
        )


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
def add_draft(request):
    invoiceForm = InvoiceForm()
    invoiceForm.fields.pop('facturationDate')
    invoiceForm.fields.pop('dueDate')
    if Invoicer.objects.filter(manager=request.user).count() < 2:
        invoiceForm.fields.pop('invoicer')
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoicer = Invoicer.objects.get(
                id=int(request.POST.get('invoicer'))
            )
        else:
            invoicer = Invoicer.objects.get(
                manager=request.user
            )
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
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


@login_required()
def add_invoice(request):
    invoiceForm = InvoiceForm()
    if Invoicer.objects.filter(manager=request.user).count() < 2:
        invoiceForm.fields.pop('invoicer')
    if request.method == 'POST':
        if request.POST.get('invoicer'):
            invoicer = Invoicer.objects.get(
                id=int(request.POST.get('invoicer'))
            )
        else:
            invoicer = Invoicer.objects.get(
                manager=request.user
            )
        invoiceData = {
            'invoicer': invoicer,
            'invoicee': Invoicee.objects.get(
                id=int(request.POST.get('invoicee'))
            ),
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
        return render(request, './invoice-form-partial.html', context)
    else:
        return render(request, './invoice-form.html', context)


# @require_POST
@login_required()
def delete_invoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    print(invoice)
    if not invoice.draft:
        return render(request, 'errorPages/405.html', status=405)
    invoice.delete()
    success(request, _('InvoiceSuccessfullyDeleted'))
    return HttpResponseRedirect(reverse('Invoice:index'))


@login_required()
def create_creditNoteOfInvoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    if invoice.draft:
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
    invoice.draft = False
    invoice.save()
    success(request, _('InvoiceSuccessfullyValidated'))
    return render(request, 'Invoice-list-item.html', {'invoice': invoice})


@login_required()
def modify_invoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    invoicerQueryset = Invoicer.objects.filter(manager=request.user)
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
        invoice.paymentMethod = request.POST.get('paymentMethod')
        invoice.baseCurrency = request.POST.get('baseCurrency')
        invoice.dueDate = request.POST.get('dueDate')
        invoice.facturationDate = request.POST.get('facturationDate')
        invoice.save()
        success(request, _('InvoiceSuccessfullyModified'))
    invoiceForm = InvoiceForm(instance=invoice)
    if invoice.estimate:
        invoiceForm.fields.pop('facturationDate')
        invoiceForm.fields.pop('dueDate')
    if invoicerQueryset.count() < 2:
        invoiceForm.fields.pop('invoicer')
    invoiceForm.fields['invoicee'].queryset = Invoicee.objects.filter(
        invoicer__in=invoicerQueryset
    )
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
    return HttpResponse(_('ProjectSaved'))


@require_POST
@login_required()
def modify_fee(request, fee):
    fee = Fee.objects.get(id=fee)
    fee.description = request.POST.getlist('description')[0]
    fee.rateUnit = Decimal(request.POST.getlist('rateUnit')[0])
    fee.vat = Decimal(request.POST.getlist('vat')[0])
    fee.count = int(request.POST.getlist('count')[0])
    fee.save()
    return HttpResponse(_('FeeSaved'))


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
    return HttpResponseRedirect(reverse('Invoice:modify', args=[invoice.id]))


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
    return HttpResponseRedirect(
        reverse('Invoice:modify', args=[project.invoice.id]),
    )


@require_POST
@login_required()
def delete_project(request, project):
    project = Project.objects.get(id=project)
    project.delete()
    return HttpResponse(_('ProjectSuccessfullyDeleted'))


@require_POST
@login_required()
def invoice_estimate(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    invoice.estimate = False
    return HttpResponse(_('EstimateSuccessfullyInvoiced'))


class HTTPResponseHXRedirect(HttpResponseRedirect):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self["HX-Redirect"] = self["Location"]

    status_code = 200


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
    return HttpResponse(_('FeeSuccesfullyDeleted'))
