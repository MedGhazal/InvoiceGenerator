from django.forms import ModelForm
from django.forms.models import (
    inlineformset_factory,
)
from django.forms import (
    DateInput,
)
from .models import Invoice, Project, Fee


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


class InvoiceForm(ModelForm):

    class Meta:
        model = Invoice
        fields = [
            'invoicer',
            'invoicee',
            'baseCurrency',
            'paymentMethod',
            'dueDate',
            'facturationDate',
        ]
        widgets = {
            'dueDate': DateInput(
                attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
            ),
            'facturationDate': DateInput(
                attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
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
