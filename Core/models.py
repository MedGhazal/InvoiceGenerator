from django.db.models import (
    TextChoices,
)
from django.utils.translation import gettext_lazy as _


class PaymentMethod(TextChoices):
    TRANSFER = 'TR', _('Bank Transfer')
    CASH = 'CS', _('Cash Payment')
    CHECK = 'CK', _('Check')
    DIVERS = 'DV', _('Divers')
