"""
Definições base de campos do engine (ajsystem).

FIELD_TYPES — mapa de tipo → props base. Usado via `'type': 'X'` na Entity.
As propriedades podem ser sobrescritas/estendidas na entidade e no form
(merge: base do tipo + props da entidade).

Tipos:
  TEXT      input de texto
  MEMO      textarea
  INT       número inteiro (align right, width 5, decimals 0)
  NUM       número flutuante (align right, width 10, decimals 2)
  ID        PK da tabela (número, não editável, label '#')
  DK        ligação filho→pai (não editável, preenchido pelo motor)
  DATA      data
  DATA_HORA data + hora
  HORA      hora
  BOOL      boolean (checkbox)
  FONE      telefone com máscara
  CPF       CPF com máscara e validação
  CNPJ      CNPJ com máscara e validação
  FK        select de referência (options do banco via query)
  LIST      select com opções fixas
  MULT10    multi-seleção de opções fixas (máx. 10, códigos 0-9 de 1 caractere; persiste códigos concatenados)
  IMAGE     imagem (preview + crop via widget)

`required` é sempre opt-in: declarado na entidade/form via `'required': True`.
"""
import re

from app.ajsystem.filters import FILTER_NUMBER, FILTER_DATE, FILTER_BOOLEAN, FILTER_SELECT


FIELD_TYPES = {
    'TEXT':      {'input': 'text'},
    'MEMO':      {'input': 'textarea'},
    'INT':       {'input': 'number', 'align': 'right', 'width': 5, 'decimals': 0},
    'NUM':       {'input': 'number', 'align': 'right', 'width': 10, 'decimals': 2},
    'ID':        {'input': 'number', 'in_form': False, 'label': '#', 'filter': FILTER_NUMBER},
    'DK':        {'input': 'number', 'in_form': False, 'filter': False},
    'DATA':      {'input': 'date', 'filter': FILTER_DATE},
    'DATA_HORA': {'input': 'datetime-local', 'filter': FILTER_DATE},
    'HORA':      {'input': 'time'},
    'BOOL':      {'input': 'boolean', 'filter': FILTER_BOOLEAN},
    'FONE':      {'input': 'text', 'mask': '(99) 99999-9999', 'digits_only': True},
    'CPF':       {'input': 'text', 'mask': '999.999.999-99', 'digits_only': True, 'validate': 'cpf'},
    'CNPJ':      {'input': 'text', 'mask': '99.999.999/9999-99', 'digits_only': True, 'validate': 'cnpj'},
    'FK':        {'input': 'select', 'filter': FILTER_SELECT},
    'LIST':      {'input': 'select', 'filter': FILTER_SELECT},
    'MULT10':    {'input': 'multi', 'filter': False},
    'IMAGE':     {'input': 'image', 'filter': False, 'required': False, 'upload_path': ''},
}


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


def fmt_mask(value, mask):
    """Aplica `mask` a `value`. Tolerante: extrai dígitos antes de formatar."""
    if value is None:
        return ''
    digits = re.sub(r'\D', '', str(value))
    if not mask:
        return digits
    out = []
    di = 0
    for ch in mask:
        if ch == '9':
            if di < len(digits):
                out.append(digits[di])
                di += 1
            else:
                break
        else:
            out.append(ch)
    return ''.join(out)
