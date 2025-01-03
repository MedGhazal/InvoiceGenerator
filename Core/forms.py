from datetime import date

from django.utils.translation import gettext as _
from django.forms import Form, DateField, DateInput
from django.forms.fields import SlugField
from django.forms.widgets import TextInput


class InvoiceFilterControlForm(Form):

    invoicee = SlugField(
        label='',
        help_text=_('INVOICEE'),
        widget=TextInput(attrs={'placeholder': _('EnterNameOfInvoicee')},)
    )
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

    invoiceeName = SlugField(
        label='',
        help_text=_('INVOICEE'),
        widget=TextInput(attrs={'placeholder': _('EnterNameOfInvoicee')},)
    )


class PaymentFilterControlForm(Form):

    payor = SlugField(
        label='',
        help_text=_('INVOICEE'),
        widget=TextInput(attrs={'placeholder': _('EnterNameOfPayor')},)
    )
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
