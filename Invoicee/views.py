from django.shortcuts import render
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
    CreateView,
)
# from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext as _

from .models import Invoicee
from Invoicer.models import Invoicer


class InvoiceeUpdateView(UpdateView, LoginRequiredMixin, SuccessMessageMixin):

    model = Invoicee
    template_name = './Invoicee-form.html'
    fields = (
        'name',
        'address',
        'ice',
        'cin',
    )
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
        invoicees = context['invoicee_list'].filter(is_person=False)
        context.update({
            'invoicee_list': invoicees,
            'private': False,
            'hasMultipleInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1
        })
        return context


class PrivateInvoiceeListView(ListView, LoginRequiredMixin):

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
        invoicees = context['invoicee_list'].filter(is_person=True)
        context.update({
            'invoicee_list': invoicees,
            'private': True,
            'hasMultipleInvoicers': Invoicer.objects.filter(
                manager=self.request.user
            ).count() > 1
        })
        return context


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


class InvoiceeCreateView(CreateView, LoginRequiredMixin, SuccessMessageMixin):

    model = Invoicee
    template_name = './Invoicee-form.html'
    fields = ('name', 'address', 'ice', 'invoicer')
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


class PrivateInvoiceeCreateView(
    CreateView,
    LoginRequiredMixin,
    SuccessMessageMixin,
):

    model = Invoicee
    template_name = './Invoicee-form.html'
    fields = ('name', 'address', 'cin',)
    success_message = _('PrivateInvoiceeInvoiceeHasBeenCreatedSuccessfully')

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
        context.update({'private': True, 'update': False})
        return context

    def post(self, request, *args, **kwargs):
        print(self.request.POST)
