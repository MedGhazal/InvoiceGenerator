from django.shortcuts import render
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
    CreateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages import success
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext as _
from django.contrib.messages import error

from .models import Invoicee
from Invoicer.models import Invoicer
from Invoice.models import Invoice
from Core.forms import InvoiceFilterControlForm, InvoiceeFilterControlForm


class InvoiceeUpdateView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):

    model = Invoicee
    template_name = './Invoicee-form.html'
    fields = ('name', 'ice', 'cin', 'address', 'country')
    success_message = _('InvoiceeSuccessfullyUpdated')

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoicee-form-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        invoiceeForm = context['form']
        invoicee = context['invoicee']
        if invoicee.is_person:
            invoiceeForm.fields.pop('ice')
        else:
            invoiceeForm.fields.pop('cin')
        context.update({
            'update': True,
            'hasMultipleInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1
        })
        return context


class InvoiceeListView(ListView, LoginRequiredMixin):

    model = Invoicee
    template_name = './Invoicee-index.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoicee-index-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault('content_type', self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        searchForm = InvoiceeFilterControlForm()
        context.update({
            'private': False,
            'hasMultipleInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1,
            'searchForm': searchForm,
        })
        return context

    def get_queryset(self, is_person=False):
        if self.request.GET.get('invoiceeName'):
            success(self.request, _('ResultsSuccessfullyFilterd'))
            queryset = Invoicee.objects.filter(
                invoicer=Invoicer.objects.get(manager=self.request.user)
            ).filter(
                name__icontains=self.request.GET['invoiceeName']
            ).filter(
                is_person=is_person
            )
        else:
            queryset = Invoicee.objects.filter(
                invoicer=Invoicer.objects.get(manager=self.request.user)
            ).filter(
                is_person=is_person
            )
        if not queryset:
            error(
                self.request,
                _('InvoicerHasNoInvoiceesOrNoInvoiceeFoundWithTheChosenFilter'),
            )
        return queryset


class PrivateInvoiceeListView(InvoiceeListView):

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({
            'private': True,
            'hasMultipleInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1
        })
        return context

    def get_queryset(self):
        return super().get_queryset(is_person=True)


class InvoiceeDetailView(DetailView, LoginRequiredMixin):

    model = Invoicee
    template_name = './Invoicee-detail.html'

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoicee-detail-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault("content_type", self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        invoicee = context['invoicee']
        if self.request.GET:
            invoiceFilterControlForm = InvoiceFilterControlForm(
                initial={
                    'beginDate': self.request.GET['beginDate'],
                    'endDate': self.request.GET['endDate'],
                },
            )
            invoices = Invoice.objects.select_related(
                'invoicee'
            ).filter(
                invoicee=invoicee
            ).filter(
                facturationDate__gte=self.request.GET['beginDate']
            ).filter(
                facturationDate__lte=self.request.GET['endDate']
            )
        else:
            invoiceFilterControlForm = InvoiceFilterControlForm(
                initial={
                    'beginDate': _('dd-mm-yy'),
                    'endDate': _('dd-mm-yy'),
                },
            )
            invoices = Invoice.objects.filter(invoicee=invoicee)
        context.update({
            'managerHasManyInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1,
            'invoices': invoices,
            'form': invoiceFilterControlForm,
        })
        return context


class InvoiceeCreateView(CreateView, LoginRequiredMixin, SuccessMessageMixin):

    model = Invoicee
    template_name = './Invoicee-form.html'
    fields = ('name', 'address', 'country', 'ice')
    success_message = _('InvoiceeHasBeenCreatedSuccessfully')

    def render_to_response(self, context, **response_kwargs):
        if self.request.META.get('HTTP_HX_REQUEST'):
            return render(
                self.request,
                './Invoicee-form-partial.html',
                context,
            )
        else:
            response_kwargs.setdefault('content_type', self.content_type)
            return self.response_class(
                request=self.request,
                template=self.get_template_names(),
                context=context,
                using=self.template_engine,
                **response_kwargs,
            )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({'private': False, 'update': False})
        return context

    def form_valid(self, form):
        form.instance.name = self.request.POST['name']
        form.instance.address = self.request.POST['address']
        if self.request.POST.get('ice'):
            form.instance.is_person = False
        else:
            form.instance.is_person = True
        form.instance.ice = self.request.POST.get('ice')
        form.instance.cin = self.request.POST.get('cin')
        if self.request.POST.get('invoicer'):
            form.instance.invoicer = Invoicer.objects.get(
                id=self.request.POST['invoicer']
            )
        else:
            form.instance.invoicer = Invoicer.objects.get(
                manager=self.request.user
            )
        response = super().form_valid(form)
        return response


class PrivateInvoiceeCreateView(InvoiceeCreateView):

    fields = ('name', 'address', 'country', 'cin')
    success_message = _('PrivateInvoiceeInvoiceeHasBeenCreatedSuccessfully')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({'private': True, 'update': False})
        return context
