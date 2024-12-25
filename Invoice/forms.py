from django.forms import ModelForm
from django.forms.models import (
    inlineformset_factory,
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
    extra=1,
    min_num=1,
    fields=['description'],
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


class ProjectForm(ModelForm):

    class Meta:
        model = Project
        fields = ['title']


class FeeForm(ModelForm):

    class Meta:
        model = Fee
        fields = ['description', 'rateUnit', 'count', 'vat']
