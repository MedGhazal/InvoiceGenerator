from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from django.contrib.messages import error
from django.urls import reverse

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee
from Invoice.models import Invoice, Project, Fee
from django.http import HttpResponseRedirect

from .forms import (
    ContactDataForm,
)
from Invoice.forms import (
    InvoiceForm,
    ProjectForm,
    FeeForm,
    FeeFormset,
)
from .utils import (
    getInvoiceesInformation,
    getInvoicesInformation,
    getPaymentMethodDistribution,
    getProjectsInformation,
    getTotalTurnoversInvoices,
)

from Core.forms import InvoiceFilterControlForm


@login_required()
def index(request, invoicer=None, beginDate=None, endDate=None):
    homeControlForm = InvoiceFilterControlForm()

    context = {}
    if request.user.is_superuser:
        invoices = Invoice.objects
    else:
        invoices = Invoice.objects.exclude(
            status=0
        ).select_related(
            'invoicer'
        ).filter(
            invoicer=Invoicer.objects.get(manager=request.user)
        )

    if request.method == 'POST':
        form = request.POST
        beginDate = form['beginDate']
        endDate = form['endDate']
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
    if request.META.get('HTTP_HX_REQUEST'):
        return render(request, 'home-index-partial.html', context)
    else:
        return render(request, 'home-index.html', context)


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
