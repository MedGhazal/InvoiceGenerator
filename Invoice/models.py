from datetime import date
from decimal import Decimal
from django.db.models import (
    Q, F, When, Case, Value, Exists,
    Model,
    ForeignKey,
    IntegerField,
    CharField,
    BooleanField,
    TextChoices,
    DateField,
    DecimalField,
    GeneratedField,
    ManyToManyField,
    CheckConstraint,
    SET_NULL,
    CASCADE,
)
from django.db.models.lookups import LessThanOrEqual
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    RegexValidator,
)
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords


class PaymentMethod(TextChoices):
    TRANSFER = 'TR', _('Bank Transfer')
    CASH = 'CS', _('Cash Payment')
    CHECK = 'CK', _('Check')
    DIVERS = 'DV', _('Divers')


class Invoice(Model):

    invoicer = ForeignKey(
        'Invoicer.Invoicer',
        on_delete=CASCADE,
        verbose_name=_('INVOICER'),
    )
    invoicee = ForeignKey(
        'Invoicee.Invoicee',
        on_delete=CASCADE,
        verbose_name=_('INVOICEE'),
    )
    count = IntegerField(
        db_default=0,
        blank=True,
        null=True,
        verbose_name=_('NUMBRE'),
    )
    baseCurrency = CharField(
        max_length=4,
        db_default='',
        validators=[
            RegexValidator(
                regex=r'[A-Z]{2,4}',
                message=_('PhoneNumberINVALID'),
            ),
        ],
        verbose_name=_('BaseCurrency'),
    )
    description = CharField(
        max_length=100,
        db_default='',
        verbose_name=_('Description'),
    )
    dueDate = DateField(
        db_default=date.today(),
        verbose_name=_('DueDate'),
        blank=True,
        null=True,
    )
    facturationDate = DateField(
        db_default=date.today(),
        verbose_name=_('FacturationDate'),
        blank=True,
        null=True,
    )
    paymentMethod = CharField(
        max_length=2,
        choices=PaymentMethod,
        default=PaymentMethod.CASH,
        verbose_name=_('PaymentMethod'),
    )
    salesAccount = IntegerField(
        db_default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(99999999),
        ],
        verbose_name=_('SalesAccount'),
    )
    vatAccount = IntegerField(
        db_default=0,
        verbose_name=_('VATAccount'),
        validators=[
            MinValueValidator(0),
            MaxValueValidator(99999999),
        ],
    )
    draft = BooleanField(
        db_default=True,
        verbose_name=_('Draft'),
        default=True,
    )
    status = GeneratedField(
        expression=Case(
            When(draft=True, then=Value(0)),
            When(
                Q(LessThanOrEqual(F('owedAmount'), F('paidAmount'))),
                then=Value(2),
            ),
            When(dueDate__lte=date.today(), then=Value(3)),
            default=1,
        ),
        output_field=IntegerField(),
        db_persist=True,
        verbose_name=_('Status'),
    )
    paidAmount = DecimalField(
        decimal_places=2,
        max_digits=8,
        db_default=0,
        verbose_name=_('PaidAmount'),
        null=True,
        blank=True,
    )
    owedAmount = DecimalField(
        decimal_places=2,
        max_digits=8,
        db_default=0,
        verbose_name=_('OwedAmount'),
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'{self.description}'

    def clean(self):
        if (
            self.dueDate is None or self.facturationDate is None
        ) and not self.draft:
            raise ValidationError(
                'DueANDFacturationDATESareMANDATORYForINVOICES'
            )
        if self.dueDate is None and self.facturationDate is not None:
            if self.dueDate < self.facturationDate:
                raise ValidationError('DueDateIsLessThanFacturationDate')

    def save(self, update_fields=None):
        invoices = Invoice.objects
        if self.draft:
            self.count = 0
        else:
            invoices = invoices.filter(
                draft=False
            ).filter(
                facturationDate__gte=f'{self.facturationDate.year}-01-01'
            ).filter(
                facturationDate__lte=f'{self.facturationDate.year}-01-01'
            )
            self.count = 1 if invoices.count() == 0 else max(
                invoice.count for invoice in invoices
            ) + 1
        super(Invoice, self).save()

    class Meta:
        verbose_name = _('INVOICE')
        verbose_name_plural = _('INVOICES')


class Project(Model):

    invoice = ForeignKey(
        'Invoice.Invoice',
        on_delete=CASCADE,
        verbose_name=_('INVOICE'),
    )
    title = CharField(
        max_length=100,
        db_default='',
        verbose_name=_('Title'),
    )

    def __str__(self):
        return f'{self.invoice}|{self.title}'

    class Meta:
        verbose_name = _('PROJECT')
        verbose_name_plural = _('PROJECTS')


class Fee(Model):

    count = IntegerField(db_default=0, verbose_name=_('COUNT'))
    vat = IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        db_default=0,
        verbose_name=_('VAT'),
    )
    rateUnit = DecimalField(
        decimal_places=2,
        max_digits=8,
        db_default=0,
        verbose_name=_('RateUnit')
    )
    description = CharField(
        max_length=100,
        db_default='',
        verbose_name=_('Description'),
    )
    project = ForeignKey(
        'Invoice.Project',
        on_delete=CASCADE,
        verbose_name=_('PROJECT'),
    )
    bookKeepingAmount = DecimalField(
        db_default=0,
        max_digits=8,
        decimal_places=2,
        verbose_name=_('BookKeepingAmount'),
    )

    def save(self, *args, **kwargs):
        super(Fee, self).save(*args, **kwargs)
        invoice = self.project.invoice
        invoice.owedAmount += self.rateUnit * self.count * Decimal(
            round(1 + self.vat / 100, 2)
        )
        invoice.save()

    def delete(self, *args, **kwargs):
        invoice = self.project.invoice
        invoice.owedAmount -= self.rateUnit * self.count * Decimal(
            round(1 + self.vat / 100, 2)
        )
        invoice.save()
        super(Fee, self).delete(*args, **kwargs)

    def __str__(self):
        return f'{self.project}-{self.description}'

    class Meta:
        verbose_name = _('Fee')
        verbose_name_plural = _('Fees')


class Payment(Model):

    paymentDay = DateField(
        db_default=date.today(),
        verbose_name=_('PaymentDay'),
    )
    paymentMethod = CharField(
        max_length=2,
        choices=PaymentMethod,
        default=PaymentMethod.CASH,
        verbose_name=_('PaymentMethod'),
    )
    paidAmount = DecimalField(
        decimal_places=2,
        max_digits=10,
        db_default=0,
        verbose_name=_('PaidAmount'),
    )
    invoice = ManyToManyField(
        'Invoice.Invoice',
        verbose_name=_('PaidInvoices'),
        related_name='paymentInvoice',
        related_query_name='paymentInvoice',
    )
    history = HistoricalRecords()

    def save(self):
        super(Payment, self).save()

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
