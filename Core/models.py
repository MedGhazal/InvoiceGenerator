from django.db.models import (
    TextChoices,
)
from django.utils.translation import gettext_lazy as _


class PaymentMethod(TextChoices):
    TRANSFER = 'TR', _('Bank Transfer')
    CASH = 'CS', _('Cash Payment')
    CHECK = 'CK', _('Check')
    CREDITNOTE = 'CN', _('CreditNote')
    CREDITCARD = 'CD', _('CreditCard')
    DEBITCARD = 'DC', _('DebitCard')
    DIRECTDEBIT = 'DD', _('DirectDebit')
    BILLOFEXCHANGE = 'BE', _('BillOfExchange')
    DIVERS = 'DV', _('Divers')


class SystemCurrency(TextChoices):
    MAD = 'MAD', _('MOROCCANDIRHAM')
    EURO = 'EURO', _('EURO')
