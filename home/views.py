from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _

from Invoice.models import Invoice

from bokeh.plotting import figure, show
from bokeh.document import Document
from bokeh.layouts import column
from bokeh.models import Slider
from bokeh.embed import server_document, components

from .forms import ContactDataForm


@login_required()
def index(request):
    # script = create_dashboard(request.build_absolute_uri())
    x = [invoice.id for invoice in Invoice.objects.all()]
    y = [float(invoice.owedAmount) for invoice in Invoice.objects.all()]
    z = [float(invoice.paidAmount) for invoice in Invoice.objects.all()]
    dashboard = figure(
        title=_('DASHBOAD'),
        x_axis_label=_('TEXT'),
        y_axis_label=_('TEXT'),
        width=300,
        height=300,
    )
    dashboard.line(x, y, line_width=2)
    dashboard.line(x, z, line_width=2)
    scripts, dashboard = components(dashboard)
    context = {
        'scripts': scripts,
        'dashboard': dashboard,
    }
    return render(request, 'home-index.html', context)


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


def create_dashboard(document) -> None:
    slider = Slider(start=0, end=30, value=0, step=1, title="Example")
    document.add_root(column(slider))
