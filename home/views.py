from decimal import Decimal
from datetime import datetime, date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _

from Invoice.models import Invoice
from Invoicee.models import Invoicee
from Invoicer.models import Invoicer

from .forms import ContactDataForm, HomeControlForm

from bokeh.plotting import figure
from bokeh.embed import components


class DateConverter:
    regex = '[0-9]{4}-[0-9]{2}-[0-9]{2}'
    format = '%Y-%m-%d'

    def to_python(self, value):
        return datetime.strftime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)


def plotInvoices(invoices):
    invoiceesPaidAmounts = {}
    for invoice in invoices:
        if invoiceesPaidAmounts.get(invoice.invoicee.name):
            invoiceesPaidAmounts[invoice.invoicee.name] += float(
                invoice.paidAmount
            )
        else:
            invoiceesPaidAmounts[invoice.invoicee.name] = float(
                invoice.paidAmount
            )
    overview = figure(
        title='Test',
        x_range=list(invoiceesPaidAmounts.keys()),
        x_axis_label='TestXAxisLabel',
        y_axis_label='TestYAxisLabel',
        # width='fit_content',
        # height=70,
    )
    overview.vbar(
        x=list(invoiceesPaidAmounts.values()),
        top=list(invoiceesPaidAmounts.keys()),
        legend_field='TestLegendField',
    )
    return components(overview)


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
    return vat, beforeVAT, afterVAT, invoice.paymentMethod


def getOutstandingAmountOfInvoicee(invoicee):
    outStandingAmount = 0
    for invoice in Invoice.objects.filter(invoicee=invoicee):
        for project in invoice.project_set.all():
            for fee in project.fee_set.all():
                outStandingAmount += round(
                    fee.rateUnit * fee.count * Decimal(1 + fee.vat / 100), 2
                )
    return outStandingAmount


@login_required()
def index(request, invoicer=None, beginDate=None, endDate=None):
    homeControlForm = HomeControlForm()
    context = {}
    invoices = Invoice.objects.exclude(
        status=0
    ).filter(
        invoicer__in=Invoicer.objects.filter(manager=request.user)
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
        invoices = invoices.filter(
            facturationDate__gte=f'{date.today().year}-01-01'
        ).filter(
            facturationDate__lte=f'{date.today().year}-12-31'
        )
    scripts, overview = plotInvoices(invoices)
    print(overview)
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
    amountPayedCash = sum(
        invoiceInformation[2] for invoiceInformation in invoicesInformation
        if invoiceInformation[3] == 'CS'
    )
    amountPayedTransfer = sum(
        invoiceInformation[2] for invoiceInformation in invoicesInformation
        if invoiceInformation[3] == 'TR'
    )
    amountPayedCheck = sum(
        invoiceInformation[2] for invoiceInformation in invoicesInformation
        if invoiceInformation[3] == 'CK'
    )
    amountPayedDivers = sum(
        invoiceInformation[2] for invoiceInformation in invoicesInformation
        if invoiceInformation[3] == 'DV'
    )
    invoiceesInformation = [
        (invoicee.name, getOutstandingAmountOfInvoicee(invoicee))
        for invoicee in Invoicee.objects.filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user)
        )
    ]
    context = {
        'numInvoices': numInvoices,
        'numOutStandingInvoices': numOutStandingInvoices,
        'sumVATPeriod': sumVATPeriod,
        'sumBeforeVATPeriod': sumBeforeVATPeriod,
        'sumAfterVATPeriod': sumAfterVATPeriod,
        'amountPayedCash': amountPayedCash,
        'amountPayedTransfer': amountPayedTransfer,
        'amountPayedCheck': amountPayedCheck,
        'amountPayedDivers': amountPayedDivers,
        'invoiceeSituation': invoiceesInformation,
        'form': homeControlForm,
        'scripts': scripts,
        'overview': overview,
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
