from datetime import date

from django.test import TestCase

from Invoice.models import (
    Invoice,
    Project,
    Fee,
)
from Invoicee.models import Invoicee
from Invoicer.models import Invoicer
from Invoice.utils import (
    parse_fee,
    parse_project,
    parse_activities,
)
from Core.exceptions import (
    LateXError,
)


class RawTEXGenerationTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
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
            id=0,
            project_id=0,
            rateUnit=1000,
            count=2,
            vat=10,
            description='TestFeeDescription',
        )
        Fee.objects.create(
            id=1,
            project_id=0,
            rateUnit=1000,
            count=2,
            vat=10,
            description='TestFeeDescription',
        )
        Invoice.objects.create(
            id=1,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            baseCurrency='MAD',
            facturationDate=date.today(),
        )
        Project.objects.create(
            id=1, invoice_id=0, title='TitleOfProjectTest',
        )
        Fee.objects.create(
            id=2, project_id=1, rateUnit=1000, count=2, vat=10,
        )

    def testParsingFees(self):
        self.maxDiff = None
        rawTEXActivityParsed = parse_fee(Fee.objects.get(id=0))[0]
        rawTEXActivity = '''
TestFeeDescription& 10\\%& 2
& \\multicolumn{1}{c}{1.000,00}
& \\multicolumn{1}{c}{2.000,00}\\\\'''
        self.assertEqual(rawTEXActivityParsed, rawTEXActivity)

    def testParsingProjects(self):
        self.maxDiff = None
        rawTEXActivitiesParsed = parse_project(
            Invoice.objects.get(id=0), Project.objects.get(id=0)
        )[0]
        rawTEXActivities = '''
\\begin{center}\\LARGE\\textbf{TitleOfProjectTest}\\end{center}
\\begin{longtable}{p{10cm}p{1cm}p{1cm}p{2cm}p{2cm}}\\\\\\hline
\\multirow{2}{*}{\\textbf{Désignation}} &
\\multirow{2}{*}{\\textbf{TVA}} &
\\multirow{2}{*}{\\textbf{QTÉ}} &
\\multirow{2}{*}{\\textbf{PU HT}} &
\\multirow{2}{*}{\\textbf{Total HT}}
\\\\\\\\\hline\hline

TestFeeDescription& 10\\%& 2
& \\multicolumn{1}{c}{1.000,00}
& \\multicolumn{1}{c}{2.000,00}\\\\
TestFeeDescription& 10\\%& 2
& \\multicolumn{1}{c}{1.000,00}
& \\multicolumn{1}{c}{2.000,00}\\\\
\\hline\\hline
\\multicolumn{4}{l}{\\textbf{Total HT (DH)}}&
\\multicolumn{1}{c}{4.000,00}\\\\
\\multicolumn{4}{l}{\\textbf{TVA (DH)}}&
\\multicolumn{1}{c}{400,00}\\\\
\\multicolumn{4}{l}{\\textbf{Total TTC (DH)}}&
\\multicolumn{1}{c}{4.400,00}\\\\\\hline
\\end{longtable}
'''
        self.assertEqual(rawTEXActivitiesParsed, rawTEXActivities)


class InvoiceValidationNoFeeParserTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
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

    def test(self):
        with self.assertRaises(LateXError):
            parse_project(Invoice.objects.get(id=0), Project.objects.get(id=0))


class InvoiceValidationNoProjectParserTestCase(TestCase):

    def setUp(self):
        Invoicer.objects.create(id=0, name='TestInvoicer')
        Invoicee.objects.create(id=0, name='TestInvoicee', invoicer_id=0)
        Invoice.objects.create(
            id=0,
            invoicer_id=0,
            invoicee_id=0,
            draft=False,
            baseCurrency='MAD',
            facturationDate=date.today(),
        )

    def test(self):
        with self.assertRaises(LateXError):
            parse_activities(Invoice.objects.get(id=0))
