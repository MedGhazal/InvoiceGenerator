from django.utils.timezone import now
from django.forms import (
    Form,
    EmailField,
    DateField,
    ModelChoiceField,
    DateInput,
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext as _

from Invoicer.models import Invoicer


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


class HomeControlForm(Form):

    invoicer = ModelChoiceField(queryset=Invoicer.objects.all())
    beginDate = DateField(
        label="",
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
        ),
        help_text=_('BeginDate'),
        initial=now,
    )
    endDate = DateField(
        label="",
        widget=DateInput(
            attrs={'type': 'date', 'pattern': r'\d{4}-\d{2}-\d{2}'}
        ),
        help_text=_('EndDate'),
        initial=now,
    )
