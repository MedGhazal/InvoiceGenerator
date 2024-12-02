from collections.abc import Iterable
from decimal import Decimal
from django.db.models.signals import (
    pre_save,
    post_save,
    pre_delete,
    m2m_changed,
)
from django.dispatch import receiver
from .models import Payment, Invoice, Project, Fee


def m2m_changed_payment_invoice_pre_add(payment):
    if payment.invoice.all().count() > 0:
        lastPayment = payment.history.last()
        coverage = Decimal(
            round(
                lastPayment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        for invoice in payment.invoice.all():
            invoice.paidAmount -= coverage
            invoice.save()


def m2m_changed_payment_invoice_post_add(payment):
    for invoice in payment.invoice.all():
        invoice.paidAmount += Decimal(
            round(
                payment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.draft = False
        invoice.save()


def m2m_changed_payment_invoice_pre_remove(payment):
    for invoice in payment.invoice.all():
        invoice.paidAmount -= Decimal(
            round(
                payment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.save()


def m2m_changed_payment_invoice_post_remove(payment):
    lastPayment = payment.history.last()
    for invoice in payment.invoice.all():
        invoice.paidAmount += Decimal(
            round(
                lastPayment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.save()


def m2m_changed_payment_invoice_pre_clear(payment):
    for invoice in payment.invoice.all():
        invoice = Invoice.objects.filter(id=id).first()
        invoice.paidAmount -= Decimal(
            round(
                payment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.save()


@receiver(m2m_changed, sender=Payment.invoice.through)
def m2m_changed_payment_invoice(
    sender=None,
    instance=None,
    action=None,
    reverse=None,
    model=None,
    pq_set=None,
    using=None,
    **kwargs,
):
    if action == 'pre_add':
        m2m_changed_payment_invoice_pre_add(instance)
    elif action == 'post_add':
        m2m_changed_payment_invoice_post_add(instance)
    elif action == 'pre_clear':
        m2m_changed_payment_invoice_pre_clear(instance)
    elif action == 'post_clear':
        pass
    elif action == 'pre_remove':
        m2m_changed_payment_invoice_pre_remove(instance)
    elif action == 'post_remove':
        m2m_changed_payment_invoice_post_remove(instance)


@receiver(pre_delete, sender=Payment)
def pre_delete_payment(**kwargs):
    if isinstance(kwargs['origin'], Iterable):
        payments = kwargs['origin']
        for payment in payments:
            invoices = payment.invoice.all()
            coverage = Decimal(round(payment.paidAmount / invoices.count(), 2))
            for invoice in invoices:
                invoice.paidAmount -= coverage
                invoice.save()
    else:
        payment = kwargs['origin']
        invoices = payment.invoice.all()
        coverage = Decimal(round(payment.paidAmount / invoices.count(), 2))
        for invoice in invoices:
            invoice.paidAmount -= coverage
            invoice.save()
