from django.contrib.auth.models import User
from django.db.models import (
    Model,
    CharField,
    ImageField,
    BooleanField,
    TextChoices,
    ForeignKey,
    OneToOneField,
    ManyToManyField,
    SET_NULL,
    CASCADE,
)
from django.core.validators import (
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
)
from django.utils.translation import gettext_lazy as _

from Core.models import SystemCurrency


class Invoicer(Model):

    class OperatingCountries(TextChoices):
        MOROCCO = 'MAR', _('MOROCCO')
        FRANCE = 'FR', _('FRANCE')

    manager = ForeignKey(
        User,
        on_delete=SET_NULL,
        null=True,
    )
    name = CharField(
        max_length=30,
        db_default='',
        verbose_name=_('NAME'),
    )
    address = CharField(
        max_length=70,
        db_default='',
        verbose_name=_('ADDRESS'),
    )
    country = CharField(
        max_length=20,
        default=OperatingCountries.MOROCCO,
        choices=OperatingCountries,
        verbose_name=_('COUNTRY'),
    )
    logo = ImageField()
    bankAccounts = ManyToManyField('BankAccount')
    telefon = CharField(
        validators=[
            RegexValidator(
                regex=r'^(0|\+\d{1,4})\d{9,15}$',
                message=_('PhoneNumberINVALID'),
            ),
        ],
        max_length=30,
        db_default='',
        verbose_name=_('TELEFONE'),
    )
    bookKeepingCurrency = CharField(
        max_length=4,
        db_default='',
        choices=SystemCurrency,
        default=SystemCurrency.MAD,
        verbose_name=_('BaseCurrency'),
    )

    @property
    def numBankAccounts(self):
        return self.bankAccounts.count()

    def __str__(self):
        return f'{self.name}'

    class Meta:
        verbose_name = _('INVOICER')
        verbose_name_plural = _('INVOICERS')


class BankAccount(Model):

    owner = ForeignKey(
        'Invoicer.Invoicer',
        related_name='Owner',
        verbose_name=_('Owner'),
        on_delete=CASCADE,
    )
    bankName = CharField(
        max_length=70,
        db_default='',
        verbose_name=_('BankName'),
        null=True,
    )
    bic = CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$',
                message=_('SWIFT/BICInvalid'),
            ),
        ],
        db_default='',
        null=True,
        verbose_name=_('BIC'),
    )
    rib = CharField(
        max_length=24,
        validators=[
            MinLengthValidator(24),
            MaxLengthValidator(24),
        ],
        db_default='',
        verbose_name=_('RIB'),
        null=True,
    )
    iban = CharField(
        max_length=26,
        validators=[
            MinLengthValidator(26),
            RegexValidator(
                regex=r'^[A-Z]{2}[A-Z0-9]*',
                message=_('BICInvalid'),
            ),
            MaxLengthValidator(26),
        ],
        db_default='',
        verbose_name=_('IBAN'),
        null=True,
    )

    def __str__(self):
        return f'{self.owner.name}:{self.bankName}'

    class Meta:
        verbose_name = _('BankAccount')
        verbose_name_plural = _('BankAccounts')


class LegalInformation(Model):

    invoicer = OneToOneField(
        'invoicer',
        on_delete=CASCADE,
    )
    ice = CharField(
        max_length=16,
        validators=[
            RegexValidator(
                regex=r'\d{14,16}',
                message=_('ICEInvalue'),
            ),
        ],
        db_default='',
        verbose_name=_('SIRET/ICE'),
    )
    rc = CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'\d{5,6}',
                message=_('REInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('RC'),
    )
    patente = CharField(
        max_length=9,
        validators=[
            RegexValidator(
                regex=r'\d{8,9}',
                message=_('REInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('PATENTE'),
    )
    cnss = CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'\d{7}',
                message=_('CNSSInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('CNSS'),
        null=True,
    )
    fiscal = CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'\d{6,8}',
                message=_('CNSSInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('IF'),
    )
    ice = CharField(
        max_length=16,
        validators=[
            RegexValidator(
                regex=r'\d{14,16}',
                message=_('ICEInvalue'),
            ),
        ],
        db_default='',
        verbose_name=_('SIRET/ICE'),
    )
    rc = CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'\d{5,6}',
                message=_('REInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('RC'),
    )
    patente = CharField(
        max_length=9,
        validators=[
            RegexValidator(
                regex=r'\d{8,9}',
                message=_('REInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('PATENTE'),
    )
    cnss = CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'\d{7}',
                message=_('CNSSInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('CNSS'),
        null=True,
    )
    fiscal = CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'\d{6,8}',
                message=_('CNSSInvalid'),
            ),
        ],
        db_default='',
        verbose_name=_('IF'),
    )
    legalForm = CharField(
        max_length=8,
        db_default='',
        verbose_name=_('LEGALFORM'),
    )

    def __str__(self):
        return f'{_('LegalInformationsOf')}:{self.invoicer.name}'

    class Meta:
        verbose_name = _('LegalInformation')
        verbose_name_plural = _('LegalInformations')
