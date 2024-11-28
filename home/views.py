from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ContactDataForm


@login_required()
def index(request):
    return render(request, 'home-index.html', {})


def register_success(request):
    return render(request, 'registration/register-success.html')


def register_user(request):
    if request.method == 'POST':
        userCreationForm = ContactDataForm(request.POST)
        if userCreationForm.is_valid():
            userCreationForm.save()
            return redirect('home:registerSuccess')
    else:
        userCreationForm = ContactDataForm()
    return render(
        request,
        'registration/register.html',
        {'form': userCreationForm},
    )
