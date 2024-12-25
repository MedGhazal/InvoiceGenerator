from django.forms import (
    EmailField,
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext as _


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
