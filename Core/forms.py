from datetime import date

from django.utils.translation import gettext as _
from django.forms import (
    Form,
    DateField,
    DateInput,
)
from django.forms.fields import SlugField


class InvoiceFilterControlForm(Form):

    invoicer = SlugField()
    invoicee = SlugField()
    beginDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}/\d{2}/\d{2}'}
        ),
        help_text=_('BeginDate'),
        initial=date.fromisoformat(f'{date.today().year}-01-01'),
    )
    endDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}/\d{2}/\d{2}'}
        ),
        help_text=_('EndDate'),
        initial=date.fromisoformat(f'{date.today().year}-12-31'),
    )


class InvoiceeFilterControlForm(Form):

    invoiceeName = SlugField()


class PaymentFilterControlForm(Form):

    payor = SlugField()

    beginDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}/\d{2}/\d{2}'}
        ),
        help_text=_('BeginDate'),
    )
    endDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}/\d{2}/\d{2}'}
        ),
        help_text=_('EndDate'),
    )
