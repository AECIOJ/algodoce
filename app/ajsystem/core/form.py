"""FORM — capacidades de persistência/coerção de formulário.

Reescrito do zero observando `core/old/form.py`. Contém os helpers de request/
DB usados por `core.do_form`. Sessions/aggs/resque adiados (Categorias não usa).
"""
import importlib, os, re
from datetime import datetime

from flask import current_app, request

from app.ajsystem.core.adapter import db
from app.ajsystem.defs.validators import resolve_validator

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


def _upload_root():
    return os.path.join(current_app.root_path, '..', 'dados', 'uploads')


def _delete_uploaded(filename):
    if not filename:
        return
    root = _upload_root()
    rel = os.path.normpath(filename)
    if rel.startswith('..') or os.path.isabs(rel):
        return
    path = os.path.join(root, rel)
    try:
        inside = os.path.commonpath([os.path.abspath(root), os.path.abspath(path)]) == os.path.abspath(root)
    except ValueError:
        inside = False
    if inside and os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


def _process_image_fields(form, instance):
    changed = set()
    for f in form._resolved_fields:
        if f.input != 'image' or f.in_form != 1:
            continue
        name = f.name
        old = getattr(instance, name, None)
        temp = request.form.get(f'temp_imagem_{name}', '').strip()
        remover = request.form.get(f'remover_imagem_{name}', '').strip() in ('1', 'on')
        if temp.startswith('temp_'):
            root = _upload_root()
            temp_path = os.path.join(root, os.path.basename(temp))
            if os.path.exists(temp_path):
                rel = (f.upload_path or '').strip('/')
                final_dir = os.path.join(root, rel) if rel else root
                os.makedirs(final_dir, exist_ok=True)
                ext = temp.rsplit('.', 1)[-1].lower()
                final = f'{instance.__class__.__tablename__}_{instance.id}_{name}.{ext}'
                final_name = f'{rel}/{final}' if rel else final
                if old:
                    _delete_uploaded(old)
                os.rename(temp_path, os.path.join(final_dir, final))
                setattr(instance, name, final_name)
        elif remover and old:
            _delete_uploaded(old)
            setattr(instance, name, None)
        if getattr(instance, name, None) != old:
            changed.add(name)
    return changed


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


def _build_nav(model, current_id):
    from sqlalchemy import text
    rows = db.session.execute(
        text(f'SELECT id FROM {model.__tablename__} ORDER BY id')
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


def _coerce(value, f):
    """Converte o valor bruto de um input para o tipo do campo."""
    if value is None:
        return None
    if f.input in ('checkbox', 'boolean'):
        return value in ('on', '1', 1, True)
    if f.input == 'number':
        s = str(value).strip()
        if not s:
            return None
        try:
            if f.decimals is not None and f.decimals > 0:
                return float(s)
            return int(s)
        except (ValueError, TypeError):
            return None
    if f.input == 'date':
        s = str(value).strip()
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None
    if f.input == 'time':
        s = str(value).strip()
        return datetime.strptime(s, '%H:%M').time() if s else None
    if f.input == 'datetime-local':
        s = str(value).strip()
        return datetime.fromisoformat(s) if s else None
    if f.input == 'multi':
        s = ''.join(sorted(value)) or None
        return s
    val = str(value).strip() or None
    if val and f.digits_only:
        val = re.sub(r'\D', '', val) or None
    if f.input == 'select' and isinstance(f.options, dict):
        for key in f.options:
            if str(key) == val:
                return key
    return val
