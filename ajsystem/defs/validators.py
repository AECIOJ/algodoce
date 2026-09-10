"""VALIDATORS — validações puras de campo (cpf/cnpj e registros).

Funções sem efeito colateral (não tocam request/DB/render). Usadas pelos
consumidores do motor (ex.: `core.do_form`) quando um `Field.validate`
referencia uma chave (`'cpf'`, `'cnpj'`) ou uma callable.

Lógica centralizada em `core/formats.py` (re-export para compat).
"""
from ajsystem.core.formats import (  # noqa: F401
    validar_cpf, validar_cnpj, VALIDATORS, resolve_validator,
)

__all__ = ['validar_cpf', 'validar_cnpj', 'VALIDATORS', 'resolve_validator']