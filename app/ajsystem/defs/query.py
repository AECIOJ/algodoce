"""Spec `Query` — referência declarativa de consulta (camada de dados).

Configuração de um select/referência: qual model consultar, campo de busca,
colunas exibidas, campo exibido e campo retornado. Aceita `str` (chave do
`MODEL_MAP`), `dict` ou a dataclass; `_resolve_query` normaliza os três
formatos.

Campos implícitos (derivados do model em `resolve_query_fields`):

- `field`          → PK do model (coluna usada como chave de busca)
- `columns`        → 1º campo string após a PK (colunas do select/modal)
- `display`        → mesmo padrão de `columns` (coluna exibida no form/list)
- `return_field`   → PK do model (coluna retornada após a seleção)
- `order`          → `display`

Ex. `carteira_id`: `Query(model='carteira', when='uso IN (0, 1)')`
  → field='id', columns/display='nome', return_field='id', order='nome'.
"""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Query:
    model: str
    field: Optional[str] = None
    columns: Optional[list[str]] = None
    display: Optional[str] = None
    return_field: Optional[str] = None
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


def resolve_query_fields(q: Optional[Query], model) -> tuple:
    """Preenche os campos implícitos do `Query` a partir do model.

    Retorna `(field, display, return_field, order)`. Sem model registrado,
    usa defaults conservadores (`id`/`nome`).
    """
    if q is None:
        return ('id', 'nome', 'id', 'nome')
    if model is None or getattr(model, '__table__', None) is None:
        return (
            q.field or 'id',
            q.display or q.field or 'nome',
            q.return_field or 'id',
            q.order or q.display or q.field or 'nome',
        )
    pk = None
    for c in model.__table__.primary_key.columns:
        pk = c.name
        break
    pk = pk or 'id'
    first_str = None
    for c in model.__table__.columns:
        if c.name == pk or c.primary_key:
            continue
        if 'String' in c.type.__class__.__name__:
            first_str = c.name
            break
    field = q.field or pk
    display = q.display or (first_str or field)
    return_field = q.return_field or pk
    order = q.order or display
    return (field, display, return_field, order)
