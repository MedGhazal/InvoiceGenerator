from django.db.models import (
    Model,
    CharField,
    ForeignKey,
    IntegerField,
    TextChoices,
    BooleanField,
    SET_NULL,
    CASCADE,
)
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.utils.translation import gettext_lazy as _


class Invoicee(Model):

    class OperatingCountries(TextChoices):
        MOROCCO = 'MAR', _('MOROCCO')
        FRANCE = 'FR', _('FRANCE')

    is_person = BooleanField(default=False)
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

    class Meta:
        verbose_name = _('INVOICEE')
        verbose_name_plural = _('INVOICEES')
