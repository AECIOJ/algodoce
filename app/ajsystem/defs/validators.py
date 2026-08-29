"""VALIDATORS — validações puras de campo (cpf/cnpj e registros).

Funções sem efeito colateral (não tocam request/DB/render). Usadas pelos
consumidores do motor (ex.: `core.do_form`) quando um `Field.validate`
referencia uma chave (`'cpf'`, `'cnpj'`) ou uma callable.
"""
import re

__all__ = ['validar_cpf', 'validar_cnpj', 'VALIDATORS']


def validar_cpf(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 11 or s == s[0] * 11:
        return False
    soma = sum(int(s[i]) * (10 - i) for i in range(9))
    d1 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    if d1 != int(s[9]):
        return False
    soma = sum(int(s[i]) * (11 - i) for i in range(10))
    d2 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    return d2 == int(s[10])


def validar_cnpj(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 14 or s == s[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w1[i] for i in range(12))
    d1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if d1 != int(s[12]):
        return False
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w2[i] for i in range(13))
    d2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return d2 == int(s[13])


VALIDATORS = {
    'cpf': validar_cpf,
    'cnpj': validar_cnpj,
}


def resolve_validator(validate):
    """Normaliza `Field.validate` numa callable de validação.

    - `str`   → chave em `VALIDATORS` ('cpf'/'cnpj').
    - callable → usada direto.
    - `None`/desconhecido → None (sem validação).
    """
    if callable(validate):
        return validate
    if isinstance(validate, str):
        return VALIDATORS.get(validate)
    if isinstance(validate, (list, tuple)):
        fns = [resolve_validator(v) for v in validate]
        return (lambda v: all(f(v) for f in fns if f)) if any(fns) else None
    return None
