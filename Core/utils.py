from babel.numbers import format_decimal
from babel.dates import format_date
from .models import PaymentMethod


def get_currency_symbol(currencyCode):
    if currencyCode == 'EURO':
        return '€'
    elif currencyCode == 'MAD':
        return 'DH'
    else:
        return ''


def get_currency_symbol_latex(currencyCode):
    if currencyCode == 'EURO':
        return '\\euro{}'
    elif currencyCode == 'MAD':
        return 'DH'
    else:
        return ''


def get_paymentMethod_label(key):
    return PaymentMethod(key).label


def lformat_decimal(decimal):
    return format_decimal(decimal, format='#,##0.00', locale='ar_MR')


def lformat_date(date):
    return format_date(date, format='full', locale='fr_FR')
