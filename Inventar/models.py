from django.db.models import (
    Model,
    CharField,
    ForeignKey,
    IntegerField,
    TextChoices,
    BooleanField,
    DecimalField,
    DateField,
    ManyToManyField,
    SET_NULL,
    CASCADE,
)
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.utils.translation import gettext_lazy as _


class Supplier(Model):

    name = CharField(
        max_length=20,
        verbose_name=_('NAME')
    )
    address = CharField(
        max_length=100,
        verbose_name=_('ADDRESS'),
        validators=[
            RegexValidator(
                regex=r'.*,.*',
                message=_('ADDRESSInvalid'),
            ),
        ],
    )

    class Meta:
        verbose_name = _('SUPPLIER')
        verbose_name_plural = _('SUPPLIERS')


class Product(Model):

    name = CharField(
        max_length=20,
        verbose_name=_('NAME'),
    )
    description = CharField(
        max_length=100,
        verbose_name=_('DESCRIPTION'),
    )
    price = DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('PRICE'),
        validators=[
            MinValueValidator(0),
        ]
    )

    class Meta:

        verbose_name = _('PRODUCT')
        verbose_name_plural = _('PRODUCTS')


class Charge(Model):

    supplier = ForeignKey(
        Supplier,
        on_delete=SET_NULL,
        null=True,
        blank=True,
    )
    entryDate = DateField(
        verbose_name=_('ENTRYDATE'),
    )
    amount = DecimalField(
        default=0,
        max_digits=10,
        decimal_places=2,
        verbose_name=_('AMOUNT'),
    )
    products = ManyToManyField(
        'Inventar.Product',
        through='ChargeProduct',
        related_name='ChargeProduct',
        verbose_name=_('CHARGEPRODUCT'),
    )

    class Meta:

        verbose_name = _('CHARGE')
        verbose_name_plural = _('CHARGES')


class ChargeProduct(Model):

    product = ForeignKey(
        'Inventar.Product',
        on_delete=CASCADE,
    )
    charge = ForeignKey(
        'Inventar.Charge',
        on_delete=CASCADE,
    )
    count = IntegerField(
        default=0,
        verbose_name=_('COUNT'),
    )

    class Meta:

        verbose_name = ('CHARGEPRODUCT')
        verbose_name_plural = _('CHARGEPRODUCTS')


class Sale(Model):

    products = ManyToManyField(
        'Inventar.Product',
        through='SaleProduct',
        related_name='SaleProduct',
        verbose_name=_('SALEPRODUCT'),
    )
    invoicee = ForeignKey(
        'Invoicee.Invoicee',
        null=True,
        on_delete=SET_NULL,
        related_name='Buyer',
        verbose_name=_('BUYER'),
    )
    saleDate = DateField(
        verbose_name=_('SALEDATE'),
    )
    amount = DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_('AMOUNT'),
    )
    discount = DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0,
        null=True,
        blank=True,
    )

    class Meta:

        verbose_name = _('SALE')
        verbose_name_plural = _('SALES')


class SaleProduct(Model):

    product = ForeignKey(
        'Inventar.Product',
        on_delete=CASCADE,
    )
    sale = ForeignKey(
        'Inventar.Sale',
        on_delete=CASCADE,
    )
    count = IntegerField(
        default=0,
        verbose_name=_('COUNT'),
    )

    class Meta:

        verbose_name = _('SALEPRODUCT')
        verbose_name_plural = _('SALEPRODUCTS')
