from itertools import chain
from decimal import Decimal

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee
from Invoice.models import Fee, Project, Invoice
from Core.utils import (
    lformat_decimal,
    get_currency_symbol,
)


def printAmountWithCurrency(amount, currencySymbol):
    if amount is None or amount <= 0:
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


def getInvoiceesInformation(user, beginDate, endDate):
    return list(
        chain.from_iterable(
            packageInvoiceeInformation(invoicee, beginDate, endDate)
            for invoicee in Invoicee.objects.filter(
                invoicer__in=Invoicer.objects.filter(manager=user)
            )
        )
    )


def getInvoicesInformation(invoices, currencies):
    return [
        (
            currency,
            invoices.filter(baseCurrency=currency).count(),
            invoices.filter(baseCurrency=currency).filter(status=3).count(),
            printAmountWithCurrency(
                sum(
                    owedAmount - paidAmount
                    for owedAmount, paidAmount in invoices.filter(
                        baseCurrency=currency
                    ).filter(
                        status__in=[3, 1]
                    ).values_list(
                        'owedAmount', 'paidAmount'
                    )
                    if paidAmount >= 0
                ),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getVATOfInvoices(invoices.filter(baseCurrency=currency)),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getBeforeVATOfInvoices(invoices.filter(baseCurrency=currency)),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                getAfterVATOfInvoices(invoices.filter(baseCurrency=currency)),
                get_currency_symbol(currency),
            ),
        )
        for currency in currencies
    ]


def getPaymentMethodDistribution(invoices, currencies):
    distributionAmountsPaidOnPaymentMethod = [
        (
            printAmountWithCurrency(
                sum(
                    invoices.filter(
                        paymentMethod='CS'
                    ).filter(
                        baseCurrency=currency
                    ).values_list(
                        'paidAmount',
                        flat=True,
                    )
                ),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                sum(
                    invoices.filter(
                        paymentMethod='TR'
                    ).filter(
                        baseCurrency=currency
                    ).values_list(
                        'paidAmount',
                        flat=True,
                    )
                ),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                sum(
                    invoices.filter(
                        paymentMethod='CK'
                    ).filter(
                        baseCurrency=currency
                    ).values_list(
                        'paidAmount',
                        flat=True,
                    )
                ),
                get_currency_symbol(currency),
            ),
            printAmountWithCurrency(
                sum(
                    invoices.filter(
                        paymentMethod='DV'
                    ).filter(
                        baseCurrency=currency
                    ).values_list(
                        'paidAmount',
                        flat=True,
                    )
                ),
                get_currency_symbol(currency),
            ),
        )
        for currency in currencies
    ]
    return {
        paymentMethod: [
            distributionAmountsPaid[i]
            for distributionAmountsPaid in distributionAmountsPaidOnPaymentMethod
        ]
        for i, paymentMethod in enumerate(['CS', 'TR', 'CK', 'DV'])
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
