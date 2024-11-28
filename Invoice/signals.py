from decimal import Decimal
from django.db.models.signals import (
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
            invoice.draft = invoice.paidAmount == 0
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
        invoice.draft = invoice.paidAmount == 0
        invoice.save()
    pass


def m2m_changed_payment_invoice_post_remove(payment):
    lastPayment = payment.history.last()
    for invoice in payment.invoice.all():
        invoice.paidAmount += Decimal(
            round(
                lastPayment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.draft = invoice.paidAmount == 0
        invoice.save()


def m2m_changed_payment_invoice_pre_clear(payment):
    for invoice in payment.invoice.all():
        invoice = Invoice.objects.filter(id=id).first()
        invoice.paidAmount -= Decimal(
            round(
                payment.paidAmount / payment.invoice.all().count(), 2
            )
        )
        invoice.draft = invoice.paidAmount == 0
        invoice.save()


@receiver(m2m_changed, sender=Payment.invoice.through)
def m2m_changed_payment_invoice(**kwargs):
    action = kwargs['action']
    print('action:', action)
    if kwargs['action'] == 'pre_add':
        m2m_changed_payment_invoice_pre_add(kwargs['instance'])
    elif kwargs['action'] == 'post_add':
        m2m_changed_payment_invoice_post_add(kwargs['instance'])
    elif kwargs['action'] == 'pre_clear':
        m2m_changed_payment_invoice_pre_clear(kwargs['instance'])
    elif kwargs['action'] == 'post_clear':
        pass
    elif kwargs['action'] == 'pre_remove':
        m2m_changed_payment_invoice_pre_remove(kwargs['instance'])
    elif kwargs['action'] == 'post_remove':
        m2m_changed_payment_invoice_post_remove(kwargs['instance'])


@receiver(pre_delete, sender=Payment)
def pre_delete_payment(**kwargs):
    querySet = kwargs['origin']
    for payment in querySet:
        invoices = payment.invoice.all()
        coverage = Decimal(round(payment.paidAmount / invoices.count(), 2))
        for invoice in invoices:
            invoice.paidAmount -= coverage
            invoice.save()
