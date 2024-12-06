from decimal import Decimal
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _

from Invoice.models import Invoice

from .forms import ContactDataForm, HomeControlForm


class DateConverter:
    regex = '[0-9]{4}-[0-9]{2}-[0-9]{2}'
    format = '%Y-%m-%d'

    def to_python(self, value):
        return datetime.strftime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)


def getInvoiceInformation(invoice):
    vat, beforeVAT, afterVAT = 0, 0, 0
    for project in invoice.project_set.all():
        for fee in project.fee_set.all():
            vat += round(
                fee.rateUnit * fee.count * fee.vat / 100, 2
            )
            beforeVAT += fee.rateUnit * fee.count
            afterVAT += round(
                fee.rateUnit * fee.count * Decimal(1 + fee.vat / 100), 2
            )
    return vat, beforeVAT, afterVAT


@login_required()
def index(request, invoicer=None, beginDate=None, endDate=None):
    homeControlForm = HomeControlForm()
    context = {}
    invoices = Invoice.objects.exclude(status=0)
    if request.method == 'POST':
        form = request.POST
        beginDate = form['beginDate']
        endDate = form['endDate']
        invoices = Invoice.objects.filter(
            facturationDate__gte=beginDate
        ).filter(
            facturationDate__lte=endDate
        )
    # elif request.method == 'GET':
    numInvoices = invoices.count()
    numOutStandingInvoices = invoices.filter(status=3).count()
    invoicesInformation = [
        getInvoiceInformation(invoice) for invoice in invoices
    ]
    sumVATPeriod = sum(
        invoiceInformation[0] for invoiceInformation in invoicesInformation
    )
    sumBeforeVATPeriod = sum(
        invoiceInformation[1] for invoiceInformation in invoicesInformation
    )
    sumAfterVATPeriod = sum(
        invoiceInformation[2] for invoiceInformation in invoicesInformation
    )
    context = {
        'numInvoices': numInvoices,
        'numOutStandingInvoices': numOutStandingInvoices,
        'sumVATPeriod': sumVATPeriod,
        'sumBeforeVATPeriod': sumBeforeVATPeriod,
        'sumAfterVATPeriod': sumAfterVATPeriod,
        'form': homeControlForm,
    }
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
