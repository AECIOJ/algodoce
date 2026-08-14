"""Spec `Query` — referência declarativa de campo (camada de dados).

Configuração de um select/referência: qual model listar, campo exibido,
filtro, ordenação. Aceita `str` (`'Product'`), `dict` ou a dataclass;
`_resolve_query` normaliza os três formatos.
"""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Query:
    model: str
    field: str = 'nome'
    columns: Optional[list[str]] = None
    when: Optional[str] = None
    order: Optional[str] = None


def _resolve_query(q: Any) -> Optional[Query]:
    if q is None:
        return None
    if isinstance(q, Query):
        return q
    if isinstance(q, str):
        return Query(model=q)
    if isinstance(q, dict):
        return Query(**q)
    return None
