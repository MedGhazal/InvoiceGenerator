from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee
from Invoice.models import Invoice
from .forms import (
    ContactDataForm,
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

    if request.GET:
        beginDate = request.GET['beginDate']
        endDate = request.GET['endDate']
    else:
        beginDate = f'{date.today().year}-01-01'
        endDate = f'{date.today().year}-12-31'

    if request.user.is_superuser:
        invoices = Invoice.objects.select_related('invoicee').exclude(
            state__in=[2, 3]
        ).filter(
            facturationDate__gte=beginDate
        ).filter(
            facturationDate__lte=endDate
        )
    else:
        invoices = Invoice.objects.select_related(
            'invoicer', 'invoicee'
        ).exclude(
            state__in=[2, 3]
        ).filter(
            invoicer=Invoicer.objects.get(manager=request.user)
        ).filter(
            facturationDate__gte=beginDate
        ).filter(
            facturationDate__lte=endDate
        )

    currencies = invoices.values_list('baseCurrency', flat=True).distinct()

    invoicesInformation = getInvoicesInformation(invoices, currencies)
    invoiceesInformation = getInvoiceesInformation(invoices, currencies)
    paymentMethodDistribution = getPaymentMethodDistribution(
        invoices,
        currencies,
    )

    projectsInformation = getProjectsInformation(invoices, currencies)
    totalTurnovers = getTotalTurnoversInvoices(invoices, currencies)

    context = {
        'beginDate': beginDate,
        'endDate': endDate,
        'numCurrencies': len(currencies),
        'invoicesInformation': invoicesInformation,
        'invoiceesInformation': invoiceesInformation,
        'projectsInformation': projectsInformation,
        'totalTurnovers': totalTurnovers,
        'paymentMethodDistribution': paymentMethodDistribution,
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
