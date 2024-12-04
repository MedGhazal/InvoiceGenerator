from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from Invoice.models import (
    Invoice,
    Project,
    Fee,
    Payment,
)
from Invoicee.models import Invoicee
from Invoicer.models import Invoicer


class InvoiceTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicer.objects.create(id=1, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            baseCurrency='MAD',
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Invoice.objects.create(
            id=2,
            invoicer_id=1,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Invoice.objects.create(id=3, invoicer_id=0, invoicee_id=0, draft=True)
        Invoice.objects.create(
            id=4,
            invoicer_id=0,
            invoicee_id=0,
            facturationDate=date.today() + timedelta(days=365),
            draft=False,
        )

    def test_count_assignment_invoice(self):
        self.assertEqual(Invoice.objects.filter(draft=False).count(), 4)
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.count, 1)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.count, 2)
        invoice = Invoice.objects.get(id=2)
        self.assertEqual(invoice.count, 1)

    def test_count_assignment_invoice_differentPeriods(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.count, 1)
        invoice = Invoice.objects.get(id=4)
        self.assertEqual(invoice.count, 1)

    def test_count_assignment_draft(self):
        invoice = Invoice.objects.get(id=3)
        self.assertEqual(invoice.count, None)

    def test_description_invoice(self):
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(
            str(invoice),
            f'{invoice.invoicer.name}|{invoice.invoicee.name}:F{invoice.count}',
        )

    def test_description_invoice_afterAddingFees(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(
            str(invoice),
            f'{invoice.invoicer.name}|{invoice.invoicee.name}:F{invoice.count}:4400.00DH',
        )

    def test_owedAmount_invoice_afterAddingFees(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.owedAmount, 4400)

    def test_description_draft(self):
        invoice = Invoice.objects.get(id=3)
        self.assertEqual(
            invoice.description,
            f'{invoice.invoicer.name}|{invoice.invoicee.name}:DEVIS',
        )


class TestInvoiceInvoiceValidationTestCase(TestCase):

    def test_dueDate_facturationDate_invoice_validation(self):
        with self.assertRaises(ValidationError):
            invoice = Invoice(
                id=4,
                invoicer_id=0,
                invoicee_id=0,
                dueDate=None,
                facturationDate=None,
                draft=False,
            )
            invoice.full_clean()

    def test_dueDate_facturationDate_invoice_validation_Databasedefault(self):
        with self.assertRaises(ValidationError):
            invoice = Invoice(
                id=4,
                invoicer_id=0,
                invoicee_id=0,
                draft=False,
            )
            invoice.full_clean()

    def test_invoice_validation_dueDateNone(self):
        with self.assertRaises(ValidationError):
            invoice = Invoice(
                id=4,
                invoicer_id=0,
                invoicee_id=0,
                dueDate=None,
                draft=False,
            )
            invoice.full_clean()

    def test_invoice_validation_facturationDateNone(self):
        with self.assertRaises(ValidationError):
            invoice = Invoice(
                id=4,
                invoicer_id=0,
                invoicee_id=0,
                facturationDate=None,
                draft=False,
            )
            invoice.full_clean()

    def test_invoice_validation_dueDateAfterFacturationDate(self):
        with self.assertRaises(ValidationError):
            invoice = Invoice(
                id=4,
                invoicer_id=0,
                invoicee_id=0,
                facturationDate=date.today(),
                dueDate=date.today() - timedelta(days=2),
                draft=False,
            )
            invoice.full_clean()


class OneInvoiceOnePaymentTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice)

    def test(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 2200)


class ManyInvoicesOnePaymentTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice_0 = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        invoice_1 = Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice_0)
        payment.invoice.add(invoice_1)

    def test(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 1100)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.paidAmount, 1100)


class ManyInvoicesOnePaymentRemoveOneInvoiceTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice_0 = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        invoice_1 = Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice_0)
        payment.invoice.add(invoice_1)
        payment.invoice.remove(invoice_1)

    def test(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 2200)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.paidAmount, 0)


class ManyInvoicesOnePaymentClearAllTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice_0 = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        invoice_1 = Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice_0)
        payment.invoice.add(invoice_1)
        payment.invoice.remove(invoice_0)
        payment.invoice.remove(invoice_1)

    def test(self):
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 0)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.paidAmount, 0)


class ManyInvoicesOnePaymentModifyTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice_0 = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        invoice_1 = Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice_0)
        payment.invoice.add(invoice_1)

    def test(self):
        payment = Payment.objects.get(id=0)
        payment.paidAmount = 2000
        payment.save()
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 1000)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.paidAmount, 1000)


class ManyInvoicesOnePaymentDeleteTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        invoice_0 = Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=0, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=0, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        invoice_1 = Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=1, project_id=0, rateUnit=1000, count=2, vat=10,
        )
        payment = Payment.objects.create(
            id=0,
            payor_id=0,
            paymentDay=date.today(),
            paidAmount=2200,
        )
        payment.invoice.add(invoice_0)
        payment.invoice.add(invoice_1)

    def test(self):
        payment = Payment.objects.get(id=0)
        payment.delete()
        invoice = Invoice.objects.get(id=0)
        self.assertEqual(invoice.paidAmount, 0)
        invoice = Invoice.objects.get(id=1)
        self.assertEqual(invoice.paidAmount, 0)
