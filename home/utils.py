from itertools import chain
from decimal import Decimal

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee
from Invoice.models import Fee, Project, Invoice
from Core.utils import (
    lformat_decimal,
    get_currency_symbol,
)
from Core.models import PaymentMethod


def printAmountWithCurrency(amount, currencySymbol):
    if amount is None or amount <= 0:
        return '-'
    else:
        return f'{lformat_decimal(amount)}{currencySymbol}'


def getVATOfInvoices(invoices):
    return sum(invoice.totalVAT for invoice in invoices)


def getBeforeVATOfInvoices(invoices):
    return sum(invoice.totalBeforeVAT for invoice in invoices)


def getAfterVATOfInvoices(invoices):
    return sum(invoice.totalAfterVAT for invoice in invoices)


def getOutstandingAmountOfInvoicee(invoicee, beginDate, endDate):
    outStandingAmount = {}
    for invoice in Invoice.objects.filter(
        invoicee=invoicee
    ).filter(
        facturationDate__gte=beginDate
    ).filter(
        facturationDate__lte=endDate
    ):
        if invoice.owedAmount > invoice.paidAmount:
            currency = get_currency_symbol(invoice.baseCurrency)
            if outStandingAmount.get(currency):
                outStandingAmount[
                    currency
                ] += invoice.owedAmount - invoice.paidAmount
            else:
                outStandingAmount[
                    currency
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
            printAmountWithCurrency(outStanding.get(currency), currency),
            printAmountWithCurrency(paid.get(currency), currency),
        )
        for currency in currencies
    ]


def getInvoiceesInformation(invoicees, beginDate, endDate):
    return list(
        chain.from_iterable(
            packageInvoiceeInformation(invoicee, beginDate, endDate)
            for invoicee in invoicees
        )
    )


def getInvoicesInformation(invoices, currencies):
    invoiceData = {}
    for currency in currencies:
        invoices = invoices.filter(baseCurrency=currency)
        paidInvoices = invoices.filter(state=3)
        outStandingInvoices = invoices.filter(state=2)
        invoiceData[currency] = (
            get_currency_symbol(currency),
            invoices.count(),
            paidInvoices.count(),
            printAmountWithCurrency(
                sum(
                    owed - paid
                    for owed, paid in outStandingInvoices.filter(
                        paidAmount__gt=0
                    ).values_list(
                        'owedAmount', 'paidAmount'
                    )
                ),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getVATOfInvoices(invoices),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getBeforeVATOfInvoices(invoices),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getAfterVATOfInvoices(invoices),
                get_currency_symbol(currency),
            ),
        )
    return invoiceData


def getPaymentMethodDistribution(invoices, currencies):
    paymentMethods = PaymentMethod.values
    paymentMethods.remove('DV')
    distributionAmountsPaidOnPaymentMethod = [
        [
            printAmountWithCurrency(
                sum(
                    invoices.filter(
                        paidAmount__gt=0
                    ).filter(
                        paymentMethod=paymentMethod
                    ).filter(
                        baseCurrency=currency
                    ).values_list(
                        'paidAmount',
                        flat=True,
                    )
                ),
                get_currency_symbol(currency),
            )
            for paymentMethod in paymentMethods
        ]
        for currency in currencies
    ]
    return {
        paymentMethod: [
            distributionAmountPaid[i]
            for distributionAmountPaid in distributionAmountsPaidOnPaymentMethod
        ]
        for i, paymentMethod in enumerate(paymentMethods)
    }


def getProjectsInformation(invoices, currencies):
    natures = set(
        Project.objects.filter(
            invoice__in=invoices
        ).values_list(
            'title', flat=True
        )
    )
    return list(
        chain.from_iterable(
            [
                [
                    nature,
                    printAmountWithCurrency(
                        sum(
                            invoice.owedAmount
                            for invoice in invoices.filter(
                                project__title=nature
                            ).filter(
                                baseCurrency=currency
                            )
                        ),
                        get_currency_symbol(currency)
                    )
                ]
                for currency in currencies
            ]
            for nature in natures
        )
    )


def getTotalTurnoversInvoices(invoices, currencies):
    return [
        (
            printAmountWithCurrency(
                sum(
                    owedAmount for owedAmount in invoices.filter(
                        baseCurrency=currency
                    ).values_list('owedAmount', flat=True)
                ),
                get_currency_symbol(currency),
            )
        )
        for currency in currencies
    ]
