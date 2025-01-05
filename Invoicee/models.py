from django.urls import reverse_lazy
from django.db.models import (
    Model,
    CharField,
    ForeignKey,
    IntegerField,
    TextChoices,
    BooleanField,
    Sum,
    CASCADE,
)
from django.db.models.expressions import F
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.utils.translation import gettext_lazy as _

from Invoice.models import Invoice
from Core.utils import get_currency_symbol


class Invoicee(Model):

    class OperatingCountries(TextChoices):
        MOROCCO = 'MAR', _('MOROCCO')
        FRANCE = 'FR', _('FRANCE')

    is_person = BooleanField(default=False, verbose_name=_('IsPerson'))
    cin = CharField(
        max_length=15,
        verbose_name=_('CIN'),
        null=True,
        blank=True,
    )
    country = CharField(
        max_length=20,
        default=OperatingCountries.MOROCCO,
        choices=OperatingCountries,
        verbose_name=_('COUNTRY'),
    )
    invoicer = ForeignKey(
        'Invoicer.Invoicer',
        on_delete=CASCADE,
        blank=False,
        verbose_name=_('INVOICER'),
    )
    ice = CharField(
        max_length=16,
        validators=[
            RegexValidator(
                regex=r'\d{14,16}',
                message=_('ICEInvalid'),
            ),
        ],
        db_default='0'*15,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('SIRET/ICE'),
    )
    name = CharField(
        max_length=30,
        db_default='',
        verbose_name=_('NAME'),
    )
    address = CharField(
        max_length=100,
        db_default='',
        validators=[
            RegexValidator(
                regex=r'.*,.*',
                message=_('ADDRESSInvalid'),
            ),
        ],
        verbose_name=_('ADDRESS'),
    )
    bookKeepingNumber = IntegerField(
        db_default=0,
        validators=[
            MaxValueValidator(99999),
            MinValueValidator(0),
        ],
        verbose_name=_('BookKeepingAccount'),
    )

    def __str__(self):
        return f'{self.name}'

    def get_absolute_url(self):
        return reverse_lazy('Invoicee:invoicee', args=[self.id])

    @property
    def outStandingAmounts(self):
        invoices = self.invoice_set.filter(state=2).filter(owedAmount__gte=0)
        currencies = invoices.values('baseCurrency').distinct().values_list(
            'baseCurrency', flat=True
        )
        return [
            {
                'currency': get_currency_symbol(currency['baseCurrency']),
                'amount': invoices.filter(
                    baseCurrency=currency
                ).annotate(
                    tbpaid=F('owedAmount')-F('paidAmount')
                ).aggregate(
                    outstanding=Sum('tbpaid')
                )['outstanding']
            }
            for currency in currencies
        ]

    @property
    def paidAmounts(self):
        invoices = self.invoice_set.filter(state=2).filter(owedAmount__gte=0)
        currencies = invoices.values('baseCurrency').distinct()
        return [
            {
                'currency': get_currency_symbol(currency['baseCurrency']),
                'amount': invoices.filter(
                    baseCurrency=currency
                ).aggregate(
                    paid=Sum('paidAmount')
                )['paid']
            }
            for currency in currencies
        ]

    @property
    def owedAmounts(self):
        invoices = self.invoice_set.filter(state=2).filter(owedAmount__gte=0)
        currencies = invoices.values('baseCurrency').distinct()
        return [
            {
                'currency': get_currency_symbol(currency['baseCurrency']),
                'amount': invoices.filter(
                    baseCurrency=currency
                ).aggregate(
                    owed=Sum('owedAmount')
                )['owed']
            }
            for currency in currencies
        ]

    class Meta:
        verbose_name = _('INVOICEE')
        verbose_name_plural = _('INVOICEES')
