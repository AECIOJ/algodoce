"""FORM — capacidades de persistência/coerção de formulário.

Reescrito do zero observando `core/old/form.py`. Contém os helpers de request/
DB usados por `core.do_form`. Sessions/aggs/resque adiados (Categorias não usa).
"""
import re
from datetime import datetime

from ajsystem.core.adapter import db
from ajsystem.defs.validators import resolve_validator

_DEFAULT_MSG_OK = 'Excluído!'
_DEFAULT_MSG_NO = 'Não é possível excluir — está em uso.'


def _has_references(instance, child_model):
    parent_table = instance.__class__.__tablename__
    for col in child_model.__table__.columns:
        if col.foreign_keys:
            for fk in col.foreign_keys:
                if fk.column.table.name == parent_table:
                    q = child_model.query.filter(getattr(child_model, col.name) == instance.id)
                    if db.session.query(q.exists()).scalar():
                        return True
    return False


def _when_allows(when, instance):
    """True se a condição `when` do delete permite excluir `instance`."""
    if when is None or when is False:
        return False
    if when is True:
        return True
    if callable(when):
        return bool(when(instance))
    items = when if isinstance(when, (list, tuple, set)) else [when]
    for item in items:
        if isinstance(item, type) and hasattr(item, '__table__'):
            if _has_references(instance, item):
                return False
        elif isinstance(item, dict):
            for field_name, empty_val in item.items():
                actual = getattr(instance, field_name, None)
                if actual is not None and actual != empty_val:
                    return False
    return True


def _resolve_delete(delete, label=None):
    """Normaliza a config de exclusão em {'when', 'msg_ok', 'msg_no'} ou None.

    `delete` aceita: False (padrão, sem exclusão), True, função `(instance)->bool`,
    set/list/tuple de classes/models (`when` por referência) ou dict
    (`{'when': ..., 'msg_ok': ..., 'msg_no': ...}`).
    """
    if delete is None or delete is False:
        return None
    if isinstance(delete, dict):
        if delete.get('when') is False:
            return None
        when = delete.get('when', True)
        msg_ok = delete.get('msg_ok')
        msg_no = delete.get('msg_no')
    else:
        when = delete
        msg_ok = None
        msg_no = None
    return {
        'when': when,
        'msg_ok': msg_ok or (f'{label} excluído!' if label else _DEFAULT_MSG_OK),
        'msg_no': msg_no or _DEFAULT_MSG_NO,
    }


def _flat_fields(form):
    return form._resolved_fields


def _is_readonly(form, instance):
    """True se o form deve ficar read-only para `instance`.

    `form.readonly` aceita False (padrão), True ou função `(instance)->bool`.
    """
    r = getattr(form, 'readonly', False)
    if not r:
        return False
    if callable(r):
        return bool(r(instance))
    return True


def _build_nav(model, current_id, fixed=None):
    from sqlalchemy import text
    where = ''
    params = {}
    for i, (mf, v) in enumerate(fixed or []):
        key = getattr(mf, 'key', None) or getattr(mf, 'name', None)
        if not key:
            continue
        where += (' AND ' if where else 'WHERE ') + f'{key} = :p{i}'
        params[f'p{i}'] = v
    rows = db.session.execute(
        text(f'SELECT id FROM {model.__tablename__} {where} ORDER BY id'),
        params,
    ).fetchall()
    ids = [r[0] for r in rows]
    idx = ids.index(current_id) if current_id in ids else -1
    return {
        'first_id': ids[0] if ids else None,
        'last_id': ids[-1] if ids else None,
        'prev_id': ids[idx - 1] if idx > 0 else None,
        'next_id': ids[idx + 1] if 0 <= idx < len(ids) - 1 else None,
    }


def _empty_value(val):
    if val is None:
        return True
    if isinstance(val, str):
        return val == ''
    if isinstance(val, (list, tuple, dict, set)):
        return len(val) == 0
    return False


# Parse de máscaras de data/hora centralizado em `core/formats.py`.
from ajsystem.core.formats import (  # noqa: F401
    _coerce_masked_datetime, _MASK_TOKENS, _MASK_TEXT_TOKENS, _MASK_TOKEN_ORDER,
    mask_strip,
)


def _coerce(value, f):
    """Converte o valor bruto de um input para o tipo do campo."""
    if value is None:
        return None
    if f.input in ('checkbox', 'boolean'):
        return value in ('on', '1', 1, True)
    if f.input == 'number':
        s = str(value).strip().replace('\u00A0', ' ')
        # sufixo de lista/readonly (`1234,56 D`) — sinal de débito/crédito
        s = re.sub(r'\s+[CD]\s*$', '', s)
        if not s:
            return None
        if ',' in s:
            # pt-BR exibido ('1.234,56'): milhar some, vírgula vira ponto.
            # Sem vírgula, ponto é decimal ('1.5') e segue intacto.
            s = s.replace(' ', '').replace('.', '').replace(',', '.')
        try:
            if f.decimals is not None and f.decimals > 0:
                return float(s)
            return int(s)
        except (ValueError, TypeError):
            return None
    if f.input in ('date', 'time', 'datetime-local'):
        s = str(value).strip()
        if not s:
            return None
        mask = getattr(f, 'mask', None)
        if mask:
            res = _coerce_masked_datetime(s, mask, f.input)
            if res is not None:
                return res
            return None
        if f.input == 'date':
            return datetime.strptime(s, '%Y-%m-%d').date()
        if f.input == 'time':
            return datetime.strptime(s, '%H:%M').time()
        return datetime.fromisoformat(s)
    if f.input == 'multi':
        s = ''.join(sorted(value)) or None
        return s
    val = str(value).strip() or None
    if val and 'R' in getattr(f, 'mask_cmds', frozenset()):
        val = mask_strip(val, f.mask_display or '') or None
    if f.input == 'select' and isinstance(f.options, dict):
        for key in f.options:
            if str(key) == val:
                return key
    return val
