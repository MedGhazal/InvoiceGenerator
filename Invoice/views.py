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
    generate_invoice_file,
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

    def get_context_data(self, *args, **kwargs):
        print(self.request.GET)
        context = super().get_context_data(*args, **kwargs)
        invoiceFilterControlForm = InvoiceFilterControlForm()
        invoicerQuerySet = Invoicer.objects.filter(
            manager=self.request.user
        )
        invoiceFilterControlForm['invoicer'].queryset = invoicerQuerySet
        invoiceFilterControlForm[
            'invoicee'
        ].queryset = Invoicee.objects.filter(invoicer__in=invoicerQuerySet)
        managerHasMultipleInvoicers = Invoicer.objects.filter(
            manager=self.request.user
        ).count() > 1
        if not managerHasMultipleInvoicers:
            invoiceFilterControlForm.fields.pop('invoicer')
        print(context)
        context['invoice_list'] = context['invoice_list'].filter(
            facturationDate__gte=self.request.GET['beginDate']
        ).filter(
            facturationDate__lte=self.request.GET['endDate']
        )
        context.update({
            'form': invoiceFilterControlForm,
            'managerHasMultipleInvoicers': managerHasMultipleInvoicers,
        })
        return context

    def get_queryset(self, *args, **kwargs):
        queryset = super().get_queryset(*args, **kwargs)
        return queryset.filter(
            invoicer__in=Invoicer.objects.filter(manager=self.request.user)
        )


class InvoiceDetailView(DetailView, LoginRequiredMixin):
    model = Invoice
    template_name = 'Invoice-detail.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        return context


@login_required()
def modify_invoice(request, invoice):
    invoice = Invoice.objects.get(id=invoice)
    invoiceForm = InvoiceForm(instance=invoice)
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
    # if request.method == 'POST':
    #     print(request)
    #     print(request.POST)
    #     print(request.method)
    # else:
    #     print(request.method)
    context = {
        'invoice': invoice,
        'invoiceForm': invoiceForm,
        'projectSet': projectSet,
        'projectForm': projectForm,
        'feeForm': feeForm,
    }
    return render(request, './Invoice-modify.html', context)


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
    return HttpResponseRedirect(
        reverse('Invoice:modify', args=[invoice.id]),
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
    return HttpResponseRedirect(
        reverse('Invoice:modify', args=[project.invoice.id]),
    )


@login_required()
def delete_project(request, project):
    project = Project.objects.get(id=project)
    project.delete()
    return HttpResponse(_('ProjectSuccessfullyDeleted'))


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
