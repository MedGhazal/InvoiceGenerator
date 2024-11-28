from glob import glob
from babel.numbers import format_decimal
from decimal import Decimal
from os import system, chdir, getcwd, remove
from os.path import join
from .models import PaymentMethod
from django.utils.translation import gettext as _
from InvoiceGenerator.settings import (
    TEMPTEXFILESDIR,
    PREFIX_CLIENT_BOOKKEEPING_MOROCCO,
    PREFIX_CLIENT_BOOKKEEPING_FRANCE,
    VAT_NOTE,
)


class LateXError(Exception):
    pass


def split_description(description):
    return ' \\cr '.join(description[i:i+50] for i in range(0, len(description), 50))


def lformat_decimal(decimal):
    return format_decimal(decimal, format='#,##0.00', locale='ar_MR')


def parse_activities(invoice):
    activities_parsed = False
    if invoice.baseCurrency == 'EUR':
        currency = '\\euro{}'
    else:
        currency = ' DH'
    activities = ''
    totalSum = 0
    for project in invoice.project_set.all():
        fees = 0
        feesVAT = 0
        feesVATIncluded = 0
        title = split_description(project.title)
        activities += f'''\\begin{{center}}\LARGE\\textbf{{{title}}}\end{{center}}
\\begin{{longtable}}{{p{{10cm}}p{{1cm}}p{{1cm}}p{{2cm}}p{{2cm}}}}\hline
\\multirow{{2}}{{*}}{{\\textbf{{Désignation}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{TVA}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{QTÉ}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{PU HT}}}} &
\\multirow{{2}}{{*}}{{\\textbf{{Total HT}}}}
\\\\\\\\\hline\hline
        '''
        project_parsed = False
        for fee in project.fee_set.all():
            project_parsed = True
            fees += fee.rateUnit * fee.count
            feesVAT += fee.rateUnit * Decimal(fee.vat / 100) * fee.count
            feesVATIncluded += fee.rateUnit * Decimal(fee.vat / 100 + 1) * fee.count
            description = split_description(fee.description)
            activities += f'''
{description}& {fee.vat}\%& {fee.count}
& \multicolumn{{1}}{{c}}{{{lformat_decimal(fee.rateUnit)}}}
& \multicolumn{{1}}{{c}}{{{lformat_decimal(fee.rateUnit * fee.count)}}}\\\\
            '''
        totalSum += fees
        activities += f'''
\hline\hline
\\multicolumn{{4}}{{l}}{{\\textbf{{Total HT ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(fees)}}}\\\\
\\multicolumn{{4}}{{l}}{{\\textbf{{TVA ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(feesVAT)}}}\\\\
\\multicolumn{{4}}{{l}}{{\\textbf{{Total TTC ({currency})}}}}&
\\multicolumn{{1}}{{c}}{{{lformat_decimal(feesVATIncluded)}}}\\\\\hline
\end{{longtable}}
        '''
        if not project_parsed:
            raise LateXError(
                _('INVOICEInvalid'),
                f'{_('ADDProjectItems')}{project}',
            )
        activities_parsed = True
    if not activities_parsed:
        raise LateXError(
            _('INVOICEInvalid'),
            f'{_('ADDProject')}{invoice}',
        )
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


def generate_invoice_tex(invoice):
    template = join(getcwd(), TEMPTEXFILESDIR, 'invoice.tex')
    with open(template, 'r', encoding='utf-8') as texFile:
        rawTex = texFile.read()
    textNote = f'\\begin{{center}}{_("VATNote")}\\end{{center}}'
    invoicer_ice_designation = get_ice_designation(invoice.invoicer)
    invoiceeCountry = get_country(invoice.invoicee)
    invoicerCountry = get_country(invoice.invoicer)
    invoicee_id = ''
    if invoice.invoicee.is_person and invoice.invoicer.country.lower() == 'mar':
        invoicee_id = f'\\textbf{{CIN}}: {invoice.invoicee.cin}\\newline'
    else:
        invoicee_ice_designation = get_ice_designation(invoice.invoicee)
        invoicee_id = f'\\textbf{{{invoicee_ice_designation}}}: {invoice.invoicee.ice}\\newline'
    isForeign = invoice.invoicee.country != invoice.invoicer.country and \
        invoice.invoicer.country.lower() == 'mar'
    invoiceStatus = ''
    activities, invoiceStatus, invoiceType = parse_activities(invoice)
    data = {
        '%INVOICEORCREDIT%': invoiceStatus,
        '%INVOICETYPE%': invoiceType,
        '%COUNT%': str(invoice.count),
        '%ACTIVITIES%': activities,
        '%INVOICERADRESS%': parse_address(invoice.invoicer.address) +
        f' {invoicerCountry}',
        '%INVOICERNAME%': invoice.invoicer.name,
        '%INVOICERFULLNAME%': f'{invoice.invoicer.name} {invoice.invoicer.legalForm}',
        '%INVOICERICE%': f'{invoicer_ice_designation}: {invoice.invoicer.ice}',
        '%RC%': invoice.invoicer.rc,
        '%PATENTE%': invoice.invoicer.patente,
        '%CNSS%': invoice.invoicer.cnss,
        '%IF%': invoice.invoicer.fiscal,
        '%TELEFON%': invoice.invoicer.telefon,
        '%INVOICEEADRESS%': parse_address(invoice.invoicee.address) +
        f'\\newline {invoiceeCountry}',
        '%INVOICEEICE%': invoicee_id,
        '%INVOICEENAME%': invoice.invoicee.name,
        '%FACTURATIONDATE%': f'{invoice.facturationDate.day}-'
        f'{invoice.facturationDate.month}-'
        f'{invoice.facturationDate.year}',
        '%FACTURATIONYEAR%': str(invoice.facturationDate.year),
        '%DUEDATE%': str(invoice.dueDate),
        '%PAYMENTMODE%': _(PaymentMethod(invoice.paymentMethod).label),
        '%NOTE%': textNote if isForeign else '',
        '%PATHTOLOGO%': str(invoice.invoicer.logo),
        '%BANKBLOCK%': parse_bankdata(
            invoice.invoicer, isDomestic=(
                invoice.baseCurrency == invoice.invoicer.bookKeepingCurrency
            )
        )
    }
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
    texFileName = f'{invoice.invoicer.name}_'\
        f'{invoice.facturationDate}_'\
        f'{invoice.count}.tex'.replace(' ', '')
    texFilePath = join(getcwd(), TEMPTEXFILESDIR, texFileName)
    with open(texFilePath, 'w', encoding='utf-8') as texFile:
        texFile.write(rawTex)
    compile_texFile(texFileName)
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
            sumFeesWithoutVAT += fee.bookKeepingAmount * Decimal(1 + fee.vat / 100)
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
