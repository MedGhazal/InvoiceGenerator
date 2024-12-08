from decimal import Decimal
from itertools import chain
from datetime import datetime, date

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _

from Invoice.models import Invoice, Fee, Project
from Invoicee.models import Invoicee
from Invoicer.models import Invoicer

from .forms import ContactDataForm, HomeControlForm

from Core.utils import (
    get_currency_symbol,
    lformat_decimal,
)


class DateConverter:
    regex = '[0-9]{4}-[0-9]{2}-[0-9]{2}'
    format = '%Y-%m-%d'

    def to_python(self, value):
        return datetime.strftime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)


def printAmountWithCurrency(amount, currencySymbol):
    if amount == 0:
        return '-'
    else:
        return f'{lformat_decimal(amount)}{currencySymbol}'


def getVATOfInvoices(invoices):
    return sum(
        round(fee.rateUnit * fee.count * Decimal(fee.vat / 100), 2)
        for fee in Fee.objects.filter(
            project__in=Project.objects.filter(
                invoice__in=invoices
            )
        )
    )


def getBeforeVATOfInvoices(invoices):
    return sum(
        fee.rateUnit * fee.count
        for fee in Fee.objects.filter(
            project__in=Project.objects.filter(
                invoice__in=invoices
            )
        )
    )


def getAfterVATOfInvoices(invoices):
    return sum(invoices.values_list('owedAmount', flat=True))


def getOutstandingAmountOfInvoicee(invoicee, beginDate, endDate):
    outStandingAmount = {}
    for invoice in Invoice.objects.filter(
        invoicee=invoicee
    ).filter(
        facturationDate__gte=beginDate
    ).filter(
        facturationDate__lte=endDate
    ):
        if invoice.owedAmount < invoice.paidAmount:
            if outStandingAmount.get(invoice.baseCurrency):
                outStandingAmount[
                    get_currency_symbol(invoice.baseCurrency)
                ] += invoice.owedAmount - invoice.paidAmount
            else:
                outStandingAmount[
                    get_currency_symbol(invoice.baseCurrency)
                ] = invoice.owedAmount - invoice.paidAmount
    return outStandingAmount


def getPaidAmountOfInvoicee(invoicee, beginDate, endDate):
    paidAmount = {}
    for invoice in Invoice.objects.filter(
        invoicee=invoicee
    ).filter(
        facturationDate__gte=beginDate
    ).filter(
        facturationDate__lte=endDate
    ):
        currencySymbol = get_currency_symbol(invoice.baseCurrency)
        if paidAmount.get(currencySymbol):
            paidAmount[currencySymbol] += invoice.paidAmount
        else:
            paidAmount[currencySymbol] = invoice.paidAmount
    return paidAmount


def packageInvoiceeInformation(invoicee, beginDate, endDate):
    paid = getPaidAmountOfInvoicee(invoicee, beginDate, endDate)
    outStanding = getOutstandingAmountOfInvoicee(invoicee, beginDate, endDate)
    currencies = set(paid.keys()).union(set(outStanding.keys()))
    return [
        (
            invoicee.name,
            invoicee.country,
            printAmountWithCurrency(
                paid[currency] if paid.get(currency) else '0',
                currency,
            ),
            printAmountWithCurrency(
                outStanding[currency] if outStanding.get(currency) else '0',
                currency,
            ),
        )
        for currency in currencies
    ]


@login_required()
def index(request, invoicer=None, beginDate=None, endDate=None):
    homeControlForm = HomeControlForm()

    if Invoicer.objects.filter(manager=request.user).count() == 0:
        currencySymbol = ''
    elif Invoicer.objects.filter(manager=request.user).count() == 1:
        currencySymbol = get_currency_symbol(
            Invoicer.objects.get(manager=request.user).bookKeepingCurrency
        )
        if not request.user.is_superuser:
            homeControlForm.fields.pop('invoicer')

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

    invoicesInformation = [
        (
            currency,
            invoices.filter(baseCurrency=currency).count(),
            invoices.filter(baseCurrency=currency).filter(status=3).count(),
            getVATOfInvoices(invoices.filter(baseCurrency=currency)),
            getBeforeVATOfInvoices(invoices.filter(baseCurrency=currency)),
            getAfterVATOfInvoices(invoices.filter(baseCurrency=currency)),
        )
        for currency in set(invoices.values_list('baseCurrency', flat=True))
    ]
    print('invoicesInformation', invoicesInformation)

    invoiceesInformation = list(chain.from_iterable([
        packageInvoiceeInformation(invoicee, beginDate, endDate)
        for invoicee in Invoicee.objects.filter(
            invoicer__in=Invoicer.objects.filter(manager=request.user)
        )
    ]))

    amountPayedCash = sum(
        invoices.filter(paymentMethod='CS').values_list('paidAmount', flat=True)
    )
    amountPayedTransfer = sum(
        invoices.filter(paymentMethod='TR').values_list('paidAmount', flat=True)
    )
    amountPayedCheck = sum(
        invoices.filter(paymentMethod='CK').values_list('paidAmount', flat=True)
    )
    amountPayedDivers = sum(
        invoices.filter(paymentMethod='DV').values_list('paidAmount', flat=True)
    )

    context = {
        'amountPayedCash': printAmountWithCurrency(
            amountPayedCash,
            currencySymbol,
        ),
        'amountPayedTransfer': printAmountWithCurrency(
            amountPayedTransfer,
            currencySymbol,
        ),
        'amountPayedCheck': printAmountWithCurrency(
            amountPayedCheck,
            currencySymbol,
        ),
        'amountPayedDivers': printAmountWithCurrency(
            amountPayedDivers,
            currencySymbol,
        ),
        'invoicesInformation': invoicesInformation,
        'invoiceesInformation': invoiceesInformation,
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
