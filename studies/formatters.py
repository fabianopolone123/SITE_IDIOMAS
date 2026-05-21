import re


def only_digits(value):
    return re.sub(r'\D+', '', value or '')


def format_cpf(value):
    digits = only_digits(value)
    if len(digits) != 11:
        return value or ''
    return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'


def format_phone(value):
    digits = only_digits(value)
    if len(digits) == 11:
        return f'({digits[:2]}) {digits[2:7]}-{digits[7:]}'
    if len(digits) == 10:
        return f'({digits[:2]}) {digits[2:6]}-{digits[6:]}'
    return value or ''


def validate_cpf_digits(value):
    digits = only_digits(value)
    if len(digits) != 11:
        raise ValueError('CPF deve ter 11 números.')
    return digits


def validate_phone_digits(value, required=True):
    digits = only_digits(value)
    if not digits and not required:
        return ''
    if len(digits) not in {10, 11}:
        raise ValueError('Telefone deve ter DDD e 10 ou 11 números.')
    return digits
