from glob import glob
from datetime import date
from decimal import Decimal
from os import system, chdir, getcwd, remove
from os.path import join
from django.utils.translation import gettext as _

from .models import Invoice, Project, Fee
from InvoiceGenerator.settings import (
    TEMPTEXFILESDIR,
    PREFIX_CLIENT_BOOKKEEPING_MOROCCO,
    PREFIX_CLIENT_BOOKKEEPING_FRANCE,
    VAT_NOTE,
)
from Core.utils import (
    get_currency_symbol_latex,
    get_paymentMethod_label,
    lformat_decimal,
    lformat_date,
)
from Core.exceptions import (
    LateXError,
)


def create_credit_note(invoice):
    invoice.paymentMethod = _('AsCreditNote')
    invoice.owedAmount = 0
    invoice.save()
    creditNote = Invoice()
    creditNote.invoicer = invoice.invoicer
    creditNote.invoicee = invoice.invoicee
    creditNote.baseCurrency = invoice.baseCurrency
    creditNote.dueDate = invoice.dueDate
    creditNote.facturationDate = invoice.facturationDate
    creditNote.paymentMethod = _('AsCreditNote')
    creditNote.salesAccount = invoice.salesAccount
    creditNote.vatAccount = invoice.vatAccount
    creditNote.draft = False
    creditNote.save()
    project = Project()
    project.invoice = creditNote
    project.title = _('CreditNote')
    project.save()
    fee = Fee()
    fee.project = project
    fee.description = f'{_('CreditNoteForTheInvoice')}: {invoice.count}'
    fee.count = 1
    fee.rateUnit = invoice.totalBeforeVAT * -1
    fee.vat = invoice.avgVAT
    creditNote.owedAmount = 0
    fee.save()


def split_description(description):
    return ' \\cr '.join(
        description[i:i+50] for i in range(0, len(description), 50)
    )


def parse_fee(fee):
    fee_ = fee.rateUnit * fee.count
    feeVAT = round(fee_ * Decimal(fee.vat / 100), 2)
    feeVATIncluded = round(fee_ * Decimal(1 + fee.vat / 100), 2)
    description = split_description(fee.description)
    activity = f'''
{description}& {fee.vat}\\%& {fee.count}
& \\multicolumn{{1}}{{c}}{{{lformat_decimal(fee.rateUnit)}}}
& \\multicolumn{{1}}{{c}}{{{lformat_decimal(fee.rateUnit * fee.count)}}}\\\\'''
    return (activity, fee_, feeVAT, feeVATIncluded)


def parse_project_header(project):
    title = split_description(project.title)
    return f'''
\\begin{{center}}\\LARGE\\textbf{{{title}}}\\end{{center}}
\\begin{{longtable}}{{p{{10cm}}p{{1cm}}p{{1cm}}p{{2cm}}p{{2cm}}}}\\\\\\hline
\\multirow{{2}}{{*}}{{\\textbf{{Désignation}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{TVA}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{QTÉ}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{PU HT}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{Total HT}}}}
\\\\\\\\\\hline\\hline
'''


def parse_project_footer(fees, feesVAT, feesVATIncluded, currency):
    return f'''
\\hline\\hline
\\multicolumn{{4}}{{l}}{{\\textbf{{Total HT ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(fees)}}}\\\\
\\multicolumn{{4}}{{l}}{{\\textbf{{TVA ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(feesVAT)}}}\\\\
\\multicolumn{{4}}{{l}}{{\\textbf{{Total TTC ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(feesVATIncluded)}}}\\\\\\hline
\\end{{longtable}}
'''


def parse_project(invoice, project):
    currency = get_currency_symbol_latex(invoice.baseCurrency)
    if project.fee_set.count() == 0:
        raise LateXError(_('INVOICEInvalid'), f'{_('ADDProject')}{invoice}')
    activities = parse_project_header(project)
    fees, feesVAT, feesVATIncluded = 0, 0, 0
    for fee in project.fee_set.all():
        activity, fee, feeVAT, feeVATIncluded = parse_fee(fee)
        fees += fee
        feesVAT += feeVAT
        feesVATIncluded += feeVATIncluded
        activities += activity
    activities += parse_project_footer(
        fees,
        feesVAT,
        feesVATIncluded,
        currency,
    )
    return (activities, fees)


def parse_activities(invoice):
    if invoice.project_set.count() == 0:
        raise LateXError(
            _('INVOICEInvalid'), f'{_('ADDProjectItems')}{invoice}'
        )
    activities = ''
    totalSum = 0
    for project in invoice.project_set.all():
        projectActivities, fees = parse_project(
            invoice,
            project,
        )
        activities += projectActivities
        totalSum += fees
    return (
        activities,
        'e facturation' if totalSum >= 0 else '\'avoir',
        'Facture' if totalSum >= 0 else 'Avoir'
    )


def parse_address(address):
    return '\\\\'.join(address.split(','))


def parse_bankdata(invoicer, isDomestic=False):
    if invoicer.hasBankData:
        bankData = f'\\textbf{{Banque}}: {invoicer.bank}\\\\'\
            f'\\textbf{{SWIFT/BIC}}: {invoicer.bic}\\\\'
        if isDomestic:
            bankData += f'\\textbf{{RIB}}: {invoicer.rib}\\\\'
        else:
            bankData += f'\\textbf{{IBAN}}: {invoicer.iban}\\\\'
        return bankData
    else:
        return ''


def get_ice_designation(institution):
    if institution.country.lower() == 'mar':
        return 'ICE'
    elif institution.country.lower() == 'fr':
        return 'SIRET'
    else:
        return ''


def get_country(institution):
    if institution.country.lower() == 'mar':
        return 'Maroc'
    elif institution.country.lower() == 'fr':
        return 'France'
    else:
        return ''


def get_invoiceeID(invoicer, invoicee):
    if invoicee.is_person and invoicer.country.lower() == 'mar':
        return f'\\textbf{{CIN}}: {invoicee.cin}\\newline'
    else:
        invoicee_ice_designation = get_ice_designation(invoicee)
        return f'\\textbf{{{invoicee_ice_designation}}}: {invoicee.ice}\\newline'


def get_invoice_block(invoice, invoiceStatus, invoiceType):
    if invoice.draft:
        return f'''
Devis Numéro: D{date.today().year}-{date.today().day}{date.today().month}\\\\
'''
    else:
        return f'''
Date d{invoiceStatus}: {lformat_date(invoice.facturationDate)}\\\\
{invoiceType} Numéro: {invoice.facturationDate.year}-{invoice.count}
'''


def get_dueDate_block(invoice):
    if (
        invoice.facturationDate is not None
        and invoice.dueDate is not None
        and not invoice.draft
    ):
        if invoice.facturationDate == invoice.dueDate:
            return 'Échéance: À la réception de la facture'
        else:
            return f'Date d\'échéance: {lformat_date(invoice.dueDate)}'
    else:
        return 'Infomation sur le devis:'


def check_invoiceIsForeign(invoicer, invoicee):
    return (
        invoicee.country != invoicer.country
        and invoicer.country.lower() == 'mar'
    )


def get_placeHolder_data(invoice):
    textNote = f'\\begin{{center}}{VAT_NOTE}\\end{{center}}'
    invoicer_ice_designation = get_ice_designation(invoice.invoicer)
    invoiceeCountry = get_country(invoice.invoicee)
    invoicerCountry = get_country(invoice.invoicer)
    invoicee_id = get_invoiceeID(invoice.invoicer, invoice.invoicee)
    isForeign = check_invoiceIsForeign(invoice.invoicer, invoice.invoicee)
    activities, invoiceStatus, invoiceType = parse_activities(invoice)
    invoiceBlock = get_invoice_block(invoice, invoiceStatus, invoiceType)
    dueDateBlock = get_dueDate_block(invoice)
    paymentMethodLabel = get_paymentMethod_label(invoice.paymentMethod)
    invoicerAddress = f'{parse_address(invoice.invoicer.address)} {invoicerCountry}'
    invoicerFullname = f'{invoice.invoicer.name} {invoice.invoicer.legalForm}'
    invoiceeAddress = f'{parse_address(invoice.invoicee.address)} {invoiceeCountry}'
    facturationPeriod = (
        str(invoice.facturationDate.year)
        if invoice.facturationDate is not None
        else date.today().year
    )
    bankBlock = parse_bankdata(
        invoice.invoicer, isDomestic=(
            invoice.baseCurrency == invoice.invoicer.bookKeepingCurrency
        )
    )
    return {
        '%COUNT%': str(invoice.count),
        '%ACTIVITIES%': activities,
        '%INVOICERADRESS%': invoicerAddress,
        '%INVOICERNAME%': invoice.invoicer.name,
        '%INVOICERFULLNAME%': invoicerFullname,
        '%INVOICERICE%': f'{invoicer_ice_designation}: {invoice.invoicer.ice}',
        '%RC%': invoice.invoicer.rc,
        '%PATENTE%': invoice.invoicer.patente,
        '%CNSS%': invoice.invoicer.cnss,
        '%IF%': invoice.invoicer.fiscal,
        '%TELEFON%': invoice.invoicer.telefon,
        '%INVOICEEADRESS%': invoiceeAddress,
        '%INVOICEEICE%': invoicee_id,
        '%INVOICEENAME%': invoice.invoicee.name,
        '%FACTURATIONYEAR%': facturationPeriod,
        '%DUEDATE%': str(invoice.dueDate),
        '%PAYMENTMODE%': _(paymentMethodLabel),
        '%NOTE%': textNote if isForeign else '',
        '%PATHTOLOGO%': str(invoice.invoicer.logo),
        '%INVOICEBLOCK%': invoiceBlock,
        '%BANKBLOCK%': bankBlock,
        '%DUEDATEBLOCK%': dueDateBlock,
    }


def generate_invoice_tex(invoice):
    template = join(getcwd(), TEMPTEXFILESDIR, 'invoice.tex')
    with open(template, 'r', encoding='utf-8') as texFile:
        rawTex = texFile.read()
    data = get_placeHolder_data(invoice)
    for key, value in data.items():
        rawTex = rawTex.replace(key, value)
    return rawTex


def compile_texFile(texFileName):
    current_path = getcwd()
    targetPath = join(getcwd(), TEMPTEXFILESDIR)
    chdir(targetPath)
    system(f'xelatex {texFileName}')
    for file in glob('*.aux'):
        remove(file)
    for file in glob('*.log'):
        remove(file)
    remove(texFileName)
    chdir(current_path)


def generate_invoice_file(invoice):
    rawTex = generate_invoice_tex(invoice)
    if invoice.draft:
        texFileName = f'{invoice.invoicer.name}_'\
            f'{date.today()}_'\
            f'{invoice.count}.tex'.replace(' ', '')
    else:
        texFileName = f'{invoice.invoicer.name}_'\
            f'{invoice.facturationDate}_'\
            f'{invoice.count}.tex'.replace(' ', '')
    texFilePath = join(getcwd(), TEMPTEXFILESDIR, texFileName)
    with open(texFilePath, 'w', encoding='utf-8') as texFile:
        texFile.write(rawTex)
    compile_texFile(texFileName)
    if invoice.draft:
        return f'{invoice.invoicer.name}_'\
            f'{date.today()}_'\
            f'{invoice.count}.pdf'.replace(' ', '')
    else:
        return f'{invoice.invoicer.name}_'\
            f'{invoice.facturationDate}_'\
            f'{invoice.count}.pdf'.replace(' ', '')


def get_bookkkeeping_prefix(invoicer):
    if invoicer.country.lower() == 'mar':
        return PREFIX_CLIENT_BOOKKEEPING_MOROCCO
    if invoicer.country.lower() == 'fr':
        return PREFIX_CLIENT_BOOKKEEPING_FRANCE
    else:
        return ''


def get_bookkeeping_padding(invoicer):
    if invoicer.country.lower() == 'mar':
        return 4
    if invoicer.country.lower() == 'fr':
        return 3
    else:
        return None


def dataCaseExport(invoice, sumFeesVE, sumFeesVEBaseCurrency):
    bookKeepingPadding = get_bookkeeping_padding(invoice.invoicer)
    if sumFeesVE >= 0:
        return [
            [
                invoice.dueDate,
                f'{get_bookkkeeping_prefix(invoice.invoicer)}'\
                f'{invoice.invoicee.bookKeepingNumber:0{bookKeepingPadding}}',
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{sumFeesVEBaseCurrency}{invoice.baseCurrency}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                sumFeesVE,
                0,
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.salesAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{sumFeesVEBaseCurrency}{invoice.baseCurrency}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                0,
                sumFeesVE,
                invoice.facturationDate,
            ],
        ]
    else:
        return [
            [
                invoice.dueDate,
                f'{get_bookkkeeping_prefix(invoice.invoicer)}'\
                f'{invoice.invoicee.bookKeepingNumber:0{bookKeepingPadding}}',
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{sumFeesVEBaseCurrency}{invoice.baseCurrency}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                0,
                sumFeesVE * -1,
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.salesAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{sumFeesVEBaseCurrency}{invoice.baseCurrency}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                sumFeesVE * -1,
                0,
                invoice.facturationDate,
            ],
        ]


def dataCaseDomesticFees(invoice, sumFees, sumFeesWithoutVAT, sumVAT):
    bookKeepingPadding = get_bookkeeping_padding(invoice.invoicer)
    if sumFees >= 0:
        return [
            [
                invoice.dueDate,
                f'{get_bookkkeeping_prefix(invoice.invoicer)}'\
                f'{invoice.invoicee.bookKeepingNumber:0{bookKeepingPadding}}',
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                round(sumFeesWithoutVAT, 2),
                0,
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.vatAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                0,
                round(sumVAT, 2),
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.salesAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                0,
                sumFees,
                invoice.facturationDate,
            ],
        ]
    else:
        return [
            [
                invoice.dueDate,
                f'{get_bookkkeeping_prefix(invoice.invoicer)}'\
                f'{invoice.invoicee.bookKeepingNumber:0{bookKeepingPadding}}',
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                0,
                round(sumFeesWithoutVAT, 2) * -1,
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.vatAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                round(sumVAT, 2) * -1,
                0,
                invoice.facturationDate,
            ],
            [
                invoice.dueDate,
                invoice.salesAccount,
                invoice.invoicee.name,
                f'FACT.{invoice.count}|{invoice.invoicee.name}',
                f'V1{invoice.count}{invoice.dueDate.year}',
                sumFees * -1,
                0,
                invoice.facturationDate,
            ],
        ]


def dectifyData(data, headers):
    return [
        {header: data_ for header, data_ in zip(headers, item)}
        for item in data
    ]


def export_invoice_data(invoice, headers):
    sumFees = 0
    sumVAT = 0
    sumFeesWithoutVAT = 0
    sumFeesVEBaseCurrency = 0
    for project in invoice.project_set.all():
        for fee in project.fee_set.all():
            sumFeesVEBaseCurrency += fee.rateUnit * fee.count
            sumFees += fee.bookKeepingAmount
            sumVAT += fee.bookKeepingAmount * Decimal(fee.vat / 100)
            sumFeesWithoutVAT += fee.bookKeepingAmount * Decimal(
                1 + fee.vat / 100
            )
    if invoice.invoicer.bookKeepingCurrency == invoice.baseCurrency:
        return dectifyData(
            dataCaseDomesticFees(invoice, sumFees, sumFeesWithoutVAT, sumVAT),
            headers,
        )
    else:
        return dectifyData(
            dataCaseExport(
                invoice,
                sumFees,
                sumFeesVEBaseCurrency,
            ),
            headers,
        )


def processInvoiceDraftDataAndSave(invoiceData, draft=True):
    invoice = Invoice()
    invoice.invoicer = invoiceData['invoicer']
    invoice.invoicee = invoiceData['invoicee']
    if not draft:
        invoice.facturationDate = date.fromisoformat(
            invoiceData['facturationDate'],
        )
        invoice.dueDate = date.fromisoformat(
            invoiceData['dueDate'],
        )
    invoice.baseCurrency = invoiceData['baseCurrency']
    invoice.paymentMethod = invoiceData['paymentMethod']
    invoice.salesAccount = 0
    invoice.vatAccount = 0
    invoice.draft = draft
    invoice.save()
    return invoice.id
