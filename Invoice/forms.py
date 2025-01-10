from django.forms import ModelForm, DateInput
from django.forms.widgets import Textarea
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Invoice, Project, Fee, Payment

from django_select2.forms import ModelSelect2Widget


class PaymentForm(ModelForm):

    def clean(self):
        invoices = self.cleaned_data['invoice']
        if self.cleaned_data.get('payor'):
            payor = self.cleaned_data['payor']
            if invoices.exclude(invoicee=payor).exists():
                raise ValidationError(
                    _('PaidInvoicesDoNotCorrespondWithTheInvoicesOfThePayor')
                )
        owedAmount = 0
        if len(set(invoices.values_list('baseCurrency', flat=True))) > 1:
            raise ValidationError(_('InvoicesHaveMoreThanOneBaseCurrency'))
        if self.instance.id:
            numInvoices = self.instance.invoice.count()
            for invoice in invoices:
                owedAmount += round(self.instance.paidAmount / numInvoices, 2)
                owedAmount += invoice.owedAmount - invoice.paidAmount
        else:
            for invoice in invoices:
                owedAmount += invoice.owedAmount - invoice.paidAmount
        if owedAmount < self.cleaned_data['paidAmount']:
            raise ValidationError(_('PaidAmountExceedsOwedAmount'))

    class Meta:
        model = Payment
        fields = [
            'payor',
            'invoice',
            'bankAccount',
            'paymentMethod',
            'paidAmount',
            'paymentDay',
        ]
        widgets = {
            'paymentDay': DateInput(
                attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
            ),
        }


class InvoiceForm(ModelForm):

    class Meta:
        model = Invoice
        fields = [
            'invoicee',
            'bankAccount',
            'baseCurrency',
            'paymentMethod',
            'facturationDate',
            'dueDate',
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
                    'class': 'invoicee-autocomplete-select',
                    'data-placeholder': _('ChooseINVOICEE'),
                    'data-minimum-input-length': 5,
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
        widgets = {'description': Textarea(attrs={'rows': 2})}
