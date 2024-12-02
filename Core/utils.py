from .models import PaymentMethod


def get_currency_symbol(currencyCode):
    if currencyCode == 'EUR':
        return '€'
    elif currencyCode == 'MAD':
        return 'DH'
    else:
        return ''


def get_currency_symbol_latex(currencyCode):
    if currencyCode == 'EUR':
        return '\\euro{}'
    elif currencyCode == 'MAD':
        return 'DH'
    else:
        return ''


def get_paymentMethod_label(key):
    return PaymentMethod(key).label
