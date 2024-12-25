from django.utils.timezone import now

from django.utils.translation import gettext as _
from django.forms import (
    Form,
    DateField,
    ModelChoiceField,
    DateInput,
)

from Invoicer.models import Invoicer
from Invoicee.models import Invoicee


class InvoiceFilterControlForm(Form):

    invoicer = ModelChoiceField(
        queryset=Invoicer.objects.all(),
        empty_label=_('Choose an invoicer'),
        label='',
        help_text=_('Invoicer'),
    )
    invoicee = ModelChoiceField(
        queryset=Invoicee.objects.all(),
        empty_label=_('Choose an invoicee'),
        label='',
        help_text=_('Invoicee'),
    )
    beginDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
        ),
        help_text=_('BeginDate'),
        initial=now,
    )
    endDate = DateField(
        label='',
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
        ),
        help_text=_('EndDate'),
        initial=now,
    )
