from django.utils.timezone import now
from django.forms import (
    ModelForm,
    EmailField,
    DateField,
    ChoiceField,
    ModelChoiceField,
    DateInput,
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext as _

from Invoicer.models import Invoicer
from Invoice.models import Invoice, Project, Fee
from Core.models import (
    PaymentMethod,
    SystemCurrency,
)


class ContactDataForm(UserCreationForm):
    email = EmailField(
        label=_('EMail'),
    )

    def save(self):
        user = super(UserCreationForm, self).save(commit=False)
        user.is_active = False
        user.save()
        return user

    class Meta:
        model = User
        fields = ('username', 'email')
