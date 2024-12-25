from datetime import datetime, date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.contrib.messages import error

from Invoicer.models import Invoicer
from Invoice.models import Invoice, Project, Fee

from .forms import (
    ContactDataForm,
)
from Invoice.forms import (
    InvoiceForm,
    ProjectForm,
    FeeForm,
)
from .utils import (
    getInvoiceesInformation,
    getInvoicesInformation,
    getPaymentMethodDistribution,
    getProjectsInformation,
    getTotalTurnoversInvoices,
)

from Core.forms import InvoiceFilterControlForm


class DateConverter:
    regex = '[0-9]{4}-[0-9]{2}-[0-9]{2}'
    format = '%Y-%m-%d'

    def to_python(self, value):
        return datetime.strftime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)


@login_required()
def index(request, invoicer=None, beginDate=None, endDate=None):
    homeControlForm = InvoiceFilterControlForm()

    if Invoicer.objects.filter(manager=request.user).count() <= 1:
        if not request.user.is_superuser:
            homeControlForm.fields.pop('invoicer')

    context = {}
    if request.user.is_superuser:
        invoices = Invoice.objects
    else:
        invoices = Invoice.objects.exclude(
            status=0
        ).filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user)
        )

    if request.method == 'POST':
        form = request.POST
        beginDate = form['beginDate']
        endDate = form['endDate']
        if form.get('invoicer'):
            invoicer = form['invoicer']
            invoices = invoices.filter(
                facturationDate__gte=beginDate
            ).filter(
                facturationDate__lte=endDate
            ).filter(
                invoicer=invoicer
            )
        else:
            invoices = invoices.filter(
                facturationDate__gte=beginDate
            ).filter(
                facturationDate__lte=endDate
            )
    elif request.method == 'GET':
        beginDate = f'{date.today().year}-01-01'
        endDate = f'{date.today().year}-12-31'
        invoices = invoices.filter(
            facturationDate__gte=beginDate
        ).filter(
            facturationDate__lte=endDate
        )

    currencies = set(invoices.values_list('baseCurrency', flat=True))

    invoicesInformation = getInvoicesInformation(invoices, currencies)
    invoiceesInformation = getInvoiceesInformation(
        request.user,
        beginDate,
        endDate,
    )

    paymentMethodDistribution = getPaymentMethodDistribution(
        invoices,
        currencies,
    )

    projectsInformation = getProjectsInformation(invoices, currencies)
    totalTurnovers = getTotalTurnoversInvoices(invoices, currencies)

    context = {
        'numCurrencies': len(currencies),
        'totalTurnovers': totalTurnovers,
        'paymentMethodDistribution': paymentMethodDistribution,
        'invoicesInformation': invoicesInformation,
        'invoiceesInformation': invoiceesInformation,
        'projectsInformation': projectsInformation,
        'form': homeControlForm,
    }
    return render(request, 'home-index.html', context)


def processInvoiceDraftDataAndSave(invoiceData, draft=True):
    invoice = Invoice()
    invoice.invoicer = invoiceData['invoicer']
    invoice.invoicee = invoiceData['invoicee']
    if not draft:
        invoice.facturationDate = invoiceData['facturationDate']
        invoice.dueDate = invoiceData['dueDate']
    invoice.baseCurrency = invoiceData['baseCurrency']
    invoice.paymentMethod = invoiceData['paymentMethod']
    invoice.salesAccount = 0
    invoice.vatAccount = 0
    invoice.draft = draft
    invoice.save()
    for projectData in invoiceData['projects']:
        project = Project()
        project.invoice = Invoice()
        project.title = projectData['title']
        project.save()
        for feeData in projectData['fees']:
            fee = Fee()
            fee.rateUnit = feeData['rateUnit']
            fee.count = feeData['count']
            fee.vat = feeData['vat']
            fee.description = feeData['description']
            fee.bookKeepingAmount = 0
            fee.save()


@login_required()
def add_invoice(request):
    invoiceForm = InvoiceForm()
    projectForm = ProjectForm()
    feeForm = FeeForm()
    invoiceData = {
        'invoicer': None,
        'invoicee': None,
        'facturationDate': None,
        'dueDate': None,
        'baseCurrency': None,
        'paymentMethod': None,
        'projects': [],
    }
    projectData = {'title': None, 'fees': []}
    feeData = {
        'description': None,
        'rateUnit': None,
        'count': None,
        'vat': None,
    }
    if request.method == 'POST':
        data = str(request.body).split('&')
        for element in data:
            field, entry = element.split('=')
            if field != 'csrfmiddlewaretoken':
                if field in (
                    'invoicer',
                    'invoicee',
                    'facturationDate',
                    'dueDate',
                    'baseCurrency',
                    'paymentMethod',
                ):
                    invoiceData[field] = entry
                elif field == 'title':
                    if len(invoiceData['projects']) > 0:
                        if len(projectData['fees']) == 0:
                            error(request, _('EmptyProjectError'))
                        else:
                            invoiceData['projects'].append(projectData)
                    projectData = {'title': entry, 'fees': []}
                elif field == 'vat':
                    feeData[field] = entry
                    projectData['fees'].append(feeData)
                    feeData = {
                        'description': None,
                        'rateUnit': None,
                        'count': None,
                        'vat': None,
                    }
                elif field in ('description', 'rateUnit', 'count'):
                    feeData[field] = entry
        processInvoiceDraftDataAndSave(invoiceData, draft=False)
    context = {
        'invoiceForm': invoiceForm,
        'projectForm': projectForm,
        'feeForm': feeForm,
        'projectIndex': 1,
        'feeIndex': 1,
    }
    return render(request, './home-add-invoice.html', context)


@login_required()
def add_draft(request):
    invoiceForm = InvoiceForm()
    del invoiceForm.fields['dueDate']
    del invoiceForm.fields['facturationDate']
    projectForm = ProjectForm()
    feeForm = FeeForm()
    invoiceData = {
        'invoicer': None,
        'invoicee': None,
        'baseCurrency': None,
        'paymentMethod': None,
        'projects': [],
    }
    projectData = {'title': None, 'fees': []}
    feeData = {
        'description': None,
        'rateUnit': None,
        'count': None,
        'vat': None,
    }
    if request.method == 'POST':
        data = str(request.body).split('&')
        for element in data:
            field, entry = element.split('=')
            if field != 'csrfmiddlewaretoken':
                if field in (
                    'invoicer',
                    'invoicee',
                    'baseCurrency',
                    'paymentMethod',
                ):
                    invoiceData[field] = entry
                elif field == 'title':
                    if len(invoiceData['projects']) > 0:
                        if len(projectData['fees']) == 0:
                            error(request, _('EmptyProjectError'))
                        else:
                            invoiceData['projects'].append(projectData)
                    projectData = {'title': entry, 'fees': []}
                elif field == 'vat':
                    feeData[field] = entry
                    projectData['fees'].append(feeData)
                    feeData = {
                        'description': None,
                        'rateUnit': None,
                        'count': None,
                        'vat': None,
                    }
                elif field in ('description', 'rateUnit', 'count'):
                    feeData[field] = entry
        processInvoiceDraftDataAndSave(invoiceData, draft=True)
    context = {
        'invoiceForm': invoiceForm,
        'projectForm': projectForm,
        'feeForm': feeForm,
        'projectIndex': 1,
        'feeIndex': 1,
    }
    return render(request, './home-add-invoice.html', context)


@login_required()
def get_project_form(request, projectIndex=1):
    projectForm = ProjectForm()
    feeForm = FeeForm()
    context = {
        'projectForm': projectForm,
        'feeForm': feeForm,
        'projectIndex': projectIndex,
        'feeIndex': 1,
    }
    return render(request, './home-project-form.html', context)


@login_required()
def get_fee_form(request, projectIndex=1, feeIndex=1):
    feeForm = FeeForm()
    context = {
        'feeForm': feeForm,
        'projectIndex': projectIndex,
        'feeIndex': feeIndex,
    }
    return render(request, './home-fee-form.html', context)


def register_success(request):
    return render(request, 'registration/register-success.html')


def register_user(request):
    if request.method == 'POST':
        userCreationForm = ContactDataForm(request.POST)
        if userCreationForm.is_valid():
            userCreationForm.save()
            return redirect('home:registerSuccess')
    else:
        userCreationForm = ContactDataForm()
    return render(
        request,
        'registration/register.html',
        {'form': userCreationForm},
    )
