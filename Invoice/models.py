from datetime import date
from decimal import Decimal

from django.urls import reverse_lazy
from django.db.models import (
    Q, F, When, Case, Value, Avg, Sum,
    Model,
    ForeignKey,
    IntegerField,
    CharField,
    DateField,
    DecimalField,
    GeneratedField,
    ManyToManyField,
    CASCADE,
)
from django.db.models.lookups import LessThanOrEqual
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.utils.translation import gettext_lazy as _
from django.db.models.expressions import DatabaseDefault
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from Core.models import (
    PaymentMethod,
    SystemCurrency,
    InvoiceStates,
)
from Core.utils import (
    get_currency_symbol,
)


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
    bankAccount = ForeignKey(
        'Invoicer.BankAccount',
        on_delete=CASCADE,
        verbose_name=_('BankAccount'),
        null=True,
        blank=True,
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
        choices=SystemCurrency,
        default=SystemCurrency.MAD,
        verbose_name=_('BaseCurrency'),
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
    state = IntegerField(
        db_default=0,
        choices=InvoiceStates,
        default=InvoiceStates.DRAFT,
        verbose_name=_('State'),
    )
    # 0: Draft or Estimate
    # 1: Validated, not paid and not overdue
    # 2: Validated and fully Paid
    # 3: Validated, not paid and overdue
    status = GeneratedField(
        expression=Case(
            When(Q(state__in=[0, 1]), then=Value(0)),
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
        if self.state == 0:
            return f'{self.invoicer}|{self.invoicee}:{_('BState')}{self.id}'
        elif self.state == 1:
            return f'{self.invoicer}|{self.invoicee}:{_('DState')}{self.id}'
        elif self.state == 4:
            return f'{self.invoicer}|{self.invoicee}:{_('CNState')}{self.count}'
        else:
            repr = f'{self.invoicer}|{self.invoicee}:{_('FState')}{self.count}'
            if self.owedAmount > 0:
                if self.owedAmount <= self.paidAmount:
                    return repr + '-'
                currencySymbol = get_currency_symbol(self.baseCurrency)
                repr += f':{self.owedAmount - self.paidAmount}{currencySymbol}'
            return repr.replace('\n', ' ')

    @property
    def number(self):
        if self.state == 0:
            return f'{date.today().year}-{_('BState')}-{self.id}'
        elif self.state == 1:
            return f'{date.today().year}-{_('DState')}-{self.id}'
        elif self.state == 4:
            return f'{self.facturationDate.year}-{_('CNSTATE')}-{self.count}'
        else:
            return f'{self.facturationDate.year}-{_('FState')}-{self.count}'

    def clean(self):
        if (
            self.dueDate is None
            or self.facturationDate is None
            or isinstance(self.dueDate, DatabaseDefault)
            or isinstance(self.facturationDate, DatabaseDefault)
        ) and self.state != 1:
            raise ValidationError(
                _('DueANDFacturationDATESareMANDATORYForINVOICES')
            )
        if self.dueDate is not None and self.facturationDate is not None:
            if self.dueDate < self.facturationDate:
                raise ValidationError(_('DueDateIsLessThanFacturationDate'))

    def save(self, *args, **kwargs):
        invoices = Invoice.objects
        self.description = f'{self.invoicer}|{self.invoicee}'
        if self.state == 0 or self.state == 1:
            self.count = None
        elif self.state == 4 and (
            self.count is None
            or isinstance(self.count, DatabaseDefault)
            or self.count == 0
        ):
            invoices = invoices.filter(
                state=4,
            ).filter(
                invoicer=self.invoicer,
            ).filter(
                facturationDate__gte=f'{self.facturationDate.year}-01-01',
            ).filter(
                facturationDate__lte=f'{self.facturationDate.year}-12-31',
            )
            self.count = 1 if invoices.count() == 0 else max(
                invoice.count for invoice in invoices
            ) + 1
        elif self.state == 2 and (
            self.count is None
            or isinstance(self.count, DatabaseDefault)
            or self.count == 0
        ):
            invoices = invoices.filter(
                state__in=[2, 3],
            ).filter(
                invoicer=self.invoicer,
            ).filter(
                facturationDate__gte=f'{self.facturationDate.year}-01-01',
            ).filter(
                facturationDate__lte=f'{self.facturationDate.year}-12-31',
            )
            self.count = 1 if invoices.count() == 0 else max(
                invoice.count for invoice in invoices
            ) + 1
        super(Invoice, self).save()

    @property
    def outstandingAmount(self):
        if self.owedAmount > 0:
            return self.owedAmount - self.paidAmount
        else:
            return 0

    @property
    def wellFormed(self):
        wellFormed = self.project_set.count() > 0
        return wellFormed and all(
            project.fee_set.count() > 0 for project in self.project_set.all()
        )

    @property
    def downloadable(self):
        return self.wellFormed

    @property
    def totalBeforeVAT(self):
        return sum(
            project.totalBeforeVAT for project in self.project_set.all()
        )

    @property
    def totalVAT(self):
        return sum(project.totalVAT for project in self.project_set.all())

    @property
    def totalAfterVAT(self):
        return sum(project.totalAfterVAT for project in self.project_set.all())

    @property
    def avgVAT(self):
        if self.project_set.all().count() > 0:
            return (
                sum(project.avgVAT for project in self.project_set.all())
                / self.project_set.count()
            )
        else:
            return 0

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

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        invoice.owedAmount -= self.totalAfterVAT
        invoice.save()
        super().delete(*args, **kwargs)

    @property
    def totalBeforeVAT(self):
        return self.fee_set.aggregate(totalBeforeVAT=Sum('rateUnit'))[
            'totalBeforeVAT'
        ]

    @property
    def totalVAT(self):
        return self.fee_set.annotate(
            VAT=F('rateUnit')*F('vat')/100
        ).aggregate(
            total=Sum('VAT')
        )['total']

    @property
    def totalAfterVAT(self):
        return self.totalBeforeVAT + self.totalVAT

    @property
    def avgVAT(self):
        return self.fee_set.aggregate(averageVAT=Avg('vat'))['averageVAT']

    @property
    def numFees(self):
        return self.fee_set.count()

    def __str__(self):
        return f'{self.invoice}|{self.title}'

    class Meta:
        verbose_name = _('PROJECT')
        verbose_name_plural = _('PROJECTS')


class Fee(Model):

    project = ForeignKey(
        'Invoice.Project',
        on_delete=CASCADE,
        verbose_name=_('PROJECT'),
    )
    rateUnit = DecimalField(
        db_default=0,
        decimal_places=2,
        max_digits=8,
        verbose_name=_('RateUnit')
    )
    count = IntegerField(db_default=0, verbose_name=_('COUNT'))
    vat = IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_default=0,
        verbose_name=_('VAT'),
    )
    description = CharField(
        max_length=100,
        db_default='',
        verbose_name=_('Description'),
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
        invoice.owedAmount += self.totalAfterVAT
        invoice.save()

    def delete(self, *args, **kwargs):
        invoice = self.project.invoice
        invoice.owedAmount -= self.totalAfterVAT
        invoice.save()
        super(Fee, self).delete(*args, **kwargs)

    @property
    def totalBeforeVAT(self):
        return self.count * self.rateUnit

    @property
    def totalVAT(self):
        return round(self.totalBeforeVAT * Decimal(self.vat / 100), 2)

    @property
    def totalAfterVAT(self):
        return round(self.totalBeforeVAT + self.totalVAT, 2)

    def get_absolute_url(self):
        return reverse_lazy('Invoice:modify', args=[self.project.invoice.id])

    def __str__(self):
        return f'{self.project}-{self.description}'

    class Meta:
        verbose_name = _('Fee')
        verbose_name_plural = _('Fees')


class Payment(Model):

    payor = ForeignKey(
        'Invoicee.Invoicee',
        on_delete=CASCADE,
        verbose_name=_('PAYOR'),
        related_name='Payor',
        default=0,
    )
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
        validators=[MinValueValidator(0)],
    )
    invoice = ManyToManyField(
        'Invoice.Invoice',
        verbose_name=_('PaidInvoices'),
        related_name='paymentInvoice',
        related_query_name='paymentInvoice',
        help_text=_('ManyToManyFieldHelpText'),
    )
    bankAccount = ForeignKey(
        'Invoicer.BankAccount',
        on_delete=CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.payor}|{self.paymentDay}'

    def save(self, *args, **kwargs):
        # lastPayment = self.history.last()
        # if lastPayment is not None:
        #     coverage = round(
        #         Decimal(lastPayment.paidAmount / self.invoice.count()),
        #         2,
        #     )
        #     for invoice in self.invoice.all():
        #         invoice.paidAmount -= coverage
        #         invoice.save()
        super(Payment, self).save()
        # numInvoices = self.invoice.count()
        # if numInvoices > 0:
        #     coverage = round(Decimal(self.paidAmount / numInvoices), 2)
        #     for invoice in self.invoice.all():
        #         invoice.paidAmount += coverage
        #         invoice.save()

    def delete(self, *args, **kwargs):
        invoices = self.invoice
        coverage = round(self.paidAmount / invoices.count(), 2)
        for invoice in invoices.all():
            invoice.paidAmount -= coverage
            invoice.state = 2
            invoice.save()
        super(Payment, self).delete()

    def get_absolute_url(self):
        return reverse_lazy('Invoice:payment', args=[self.id])

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
