from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from django.forms import DateInput
from django.utils.translation import gettext_lazy as _

from Invoicee.models import Invoicee
from .models import Invoice, Project, Fee, Payment

from django_select2.forms import ModelSelect2Widget


ProjectFormset = inlineformset_factory(
    Invoice,
    Project,
    extra=0,
    min_num=1,
    fields=['title'],
    exclude=[],
)
FeeFormset = inlineformset_factory(
    Project,
    Fee,
    can_delete_extra=False,
    extra=0,
    min_num=1,
    fields=['description', 'rateUnit', 'count', 'vat'],
    exclude=['bookKeepingAmount'],
)


class PaymentForm(ModelForm):

    class Meta:
        model = Payment
        fields = [
            'payor',
            'invoice',
            'bankAccount',
            'paidAmount',
            'paymentDay',
            'paymentMethod',
        ]
        widgets = {
            'paymentDay': DateInput(
                attrs={
                    'type': 'date',
                    'pattern': r'\d{4}-\d{2}-\d{2}',
                }
            ),
        }


class InvoiceForm(ModelForm):

    class Meta:
        model = Invoice
        fields = [
            'invoicer',
            'invoicee',
            'bankAccount',
            'baseCurrency',
            'paymentMethod',
            'dueDate',
            'facturationDate',
        ]
        widgets = {
            'dueDate': DateInput(
                attrs={
                    'type': 'date',
                    'pattern': r'\d{4}-\d{2}-\d{2}',
                    'required': True,
                }
            ),
            'facturationDate': DateInput(
                attrs={
                    'type': 'date',
                    'pattern': r'\d{4}-\d{2}-\d{2}',
                    'required': True,
                }
            ),
            'invoicee': ModelSelect2Widget(
                search_fields=['name__icontains'],
                attrs={
                    'data-placeholder': _('ChooseINVOICEE'),
                    'id': 'invoicee',
                }
            ),
        }


class ProjectForm(ModelForm):

    class Meta:
        model = Project
        fields = ['title']


class FeeForm(ModelForm):

    class Meta:
        model = Fee
        fields = ['description', 'rateUnit', 'count', 'vat']
