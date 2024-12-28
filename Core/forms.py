from datetime import date

from django.utils.timezone import now

from django.utils.translation import gettext as _
from django.forms import (
    Form,
    DateField,
    DateInput,
)


class InvoiceFilterControlForm(Form):

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
