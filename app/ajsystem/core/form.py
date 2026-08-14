import importlib, os, re
from datetime import datetime
from flask import request, current_app
from sqlalchemy import text
from app.ajsystem.core.adapter import db
from app.ajsystem.defs.form import Form, _resolve_label  # noqa: F401
from app.ajsystem.defs.entities import MODEL_MAP, _entidade_fields
from app.ajsystem.core.utils import item_ref, deep_attr


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


def can_delete(instance, delete_when):
    if not delete_when:
        return True
    items = delete_when if isinstance(delete_when, (list, tuple, set)) else [delete_when]
    for item in items:
        if isinstance(item, type) and issubclass(item, db.Model):
            if _has_references(instance, item):
                return False
        elif isinstance(item, dict):
            for field_name, empty_val in item.items():
                actual = getattr(instance, field_name, None)
                if actual is not None and actual != empty_val:
                    return False
    return True


def em_uso(instance, models):
    """True se o registro é referenciado por algum dos modelos (FKs)."""
    models = models if isinstance(models, (list, tuple)) else [models]
    return any(_has_references(instance, m) for m in models)


def _pesquise_model(campo):
    """Resolve o model de `campo` (classe, entidade, slug ou nome de tabela)."""
    if isinstance(campo, type):
        return campo if getattr(campo, '__table__', None) is not None else None
    key = str(campo).strip()
    if key in MODEL_MAP:
        return MODEL_MAP[key]
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
    if snake in MODEL_MAP:
        return MODEL_MAP[snake]
    low = key.lower()
    if low in MODEL_MAP:
        return MODEL_MAP[low]
    for m in MODEL_MAP.values():
        if getattr(m, '__tablename__', None) == low:
            return m
        if getattr(m, '__name__', '').lower() == low:
            return m
    return None


def pesquise(campo, valor, retorno, destino=None, por=None):
    """Pesquisa genérica (utilitário reutilizável em qualquer módulo).

    `pesquise(Campo a pesquisar, Valor pesquisado, Campo a ser retornado,
    variavel a ser modificada)` -> True/False.

    Ex.: ok = pesquise('cliente', 5, 'nome', item)  # item.nome = nome
         nome = pesquise('cliente', 5, 'nome')      # devolve o valor
         ok = pesquise(Cliente, 'Ana', 'id', item, 'nome')  # por outro campo

    `campo` aceita o model, o nome da entidade ('Cliente'/'cliente') ou a
    tabela ('clientes'). `por` é o campo de busca (default: chave primária).
    Com `destino` (objeto com atributo `retorno` ou dict), grava e retorna
    True quando encontra, False caso contrário. Sem `destino`, devolve o valor
    encontrado (ou None).
    """
    model = _pesquise_model(campo)
    if model is None:
        return False if destino is not None else None
    table = getattr(model, '__table__', None)
    if table is None:
        return False if destino is not None else None
    cols = set(table.columns.keys())
    pk = next((c.name for c in table.primary_key.columns), 'id')
    por = por or pk
    if por not in cols or retorno not in cols:
        return False if destino is not None else None
    record = model.query.filter(getattr(model, por) == valor).first()
    if record is None:
        return False if destino is not None else None
    value = getattr(record, retorno, None)
    if destino is None:
        return value
    if isinstance(destino, dict):
        destino[retorno] = value
    elif hasattr(destino, retorno):
        setattr(destino, retorno, value)
    return True


_DEFAULT_MSG_OK = 'Excluído!'
_DEFAULT_MSG_NO = 'Não é possível excluir — está em uso.'


def _resolve_delete(delete, delete_when=None, flash_deny=None, flash_excluido=None, label=None):
    """Normaliza a config de exclusão em {'when', 'msg_ok', 'msg_no'} ou None.

    `delete` aceita: False/None (desabilita), True (habilita) ou dict com as
    chaves `when` (False desabilita; set/list de modelos para checagem FK via
    `can_delete`; callable `(instance) -> bool`; True/ausente = sempre permite),
    `msg_ok` (sucesso) e `msg_no` (bloqueado). Mantém fallback legado para
    `delete_when`, `flash_deny` e `flash_excluido` quando o dict não os define.
    """
    if delete is None or delete is False:
        return None
    if isinstance(delete, dict):
        when = delete.get('when', delete_when or True)
        if when is False:
            return None
        msg_ok = delete.get('msg_ok') or flash_excluido
        msg_no = delete.get('msg_no') or flash_deny
    else:
        when = delete_when or True
        msg_ok = flash_excluido
        msg_no = flash_deny
    return {
        'when': when,
        'msg_ok': msg_ok or (f'{label} excluído!' if label else _DEFAULT_MSG_OK),
        'msg_no': msg_no or _DEFAULT_MSG_NO,
    }


def _when_allows(when, instance):
    """True se a condição `when` do delete permite excluir `instance`."""
    if when is None or when is False:
        return False
    if when is True:
        return True
    if callable(when):
        return bool(when(instance))
    return can_delete(instance, when)


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
    """Aplica uploads temporarios e exclusoes de campos image (somente no salvar)."""
    changed = set()
    for f in form._resolved_fields:
        if f.input != 'image' or not f.in_form:
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
    if not form.readonly_when or not instance:
        return False
    for k, v in form.readonly_when.items():
        actual = getattr(instance, k, None)
        if callable(v):
            if not v(actual):
                return False
        elif isinstance(v, (list, tuple, set)):
            if actual not in v:
                return False
        else:
            if actual != v:
                return False
    return True


def _build_nav(model, current_id):
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


def _field_raw(form_data, prefix, f):
    """Valor bruto de um campo; para `multi`, concatena os checkboxes marcados."""
    if f.input == 'multi':
        return ''.join(sorted(form_data.getlist(prefix + f.name)))
    return form_data.get(prefix + f.name)


def _coerce_field_value(f, raw):
    """Converte o valor bruto de um input para o tipo do campo (linhas filhas).

    Espelha a conversão do formulário principal; para `select` com options em
    dict, normaliza o valor para o tipo da chave correspondente (int/str).
    """
    if raw is None:
        return None
    if f.input in ('checkbox', 'boolean'):
        return raw in ('on', '1', 1, True)
    if f.input == 'number':
        s = str(raw).strip()
        if not s:
            return None
        try:
            if f.decimals is not None and f.decimals > 0:
                return float(s)
            return int(s)
        except (ValueError, TypeError):
            return None
    if f.input == 'date':
        s = str(raw).strip()
        return datetime.strptime(s, '%Y-%m-%d').date() if s else None
    if f.input == 'time':
        s = str(raw).strip()
        return datetime.strptime(s, '%H:%M').time() if s else None
    if f.input == 'datetime-local':
        s = str(raw).strip()
        return datetime.fromisoformat(s) if s else None
    val = str(raw).strip() or None
    if val and f.digits_only:
        val = re.sub(r'\D', '', val) or None
    if f.input == 'select' and isinstance(f.options, dict):
        for key in f.options:
            if str(key) == val:
                return key
    return val


def _set_parent_child(child_model, parent_model, child, instance):
    """Liga um filho ao pai (FK) via relação quando possível."""
    if parent_model is None or child_model is None:
        return
    mapper = getattr(child_model, '__mapper__', None)
    if mapper is not None:
        for name, rel in mapper.relationships.items():
            if rel.mapper.class_ is parent_model:
                setattr(child, name, instance)
                return
    for col in child_model.__table__.columns:
        for fk in col.foreign_keys:
            if fk.column.table is parent_model.__table__:
                setattr(child, col.name, instance.id)
                return


def _empty_value(val):
    if val is None:
        return True
    if isinstance(val, str):
        return val == ''
    if isinstance(val, (list, tuple, dict, set)):
        return len(val) == 0
    return False


def _save_session_children(form, instance, form_data):
    """Persistência genérica das sessions auto-derivadas.

    Parseia os inputs `child_<rel>_<rid>_<campo>` do renderizador padrão.
    Regras:
    - linha ignorada quando todos os campos editáveis estão vazios ou falta
      algum campo `required`;
    - rid numérico = registro existente (upsert); rid `n*` = novo;
    - FK para o pai preenchida automaticamente;
    - registros existentes não submetidos são excluídos.
    """
    if not form._resolved_sessions:
        return
    for session in form._resolved_sessions:
        if session.get('template'):
            continue
        if session.get('readonly'):
            continue
        rel_name = session['attr']
        child_model = session.get('model')
        if child_model is None:
            continue
        fields = [f for f in session.get('fields', []) if f.in_form]
        if not fields:
            continue
        prefix = 'child_' + rel_name + '_'
        raw = getattr(instance, rel_name, None)
        if session.get('single'):
            existing = [raw] if raw is not None else []
        elif raw is None:
            existing = []
        else:
            existing = raw.all() if hasattr(raw, 'all') and callable(raw.all) else list(raw)
        if session.get('single'):
            row = {}
            has_val = False
            missing_required = False
            for f in fields:
                val = _coerce_field_value(f, _field_raw(form_data, prefix, f))
                row[f.name] = val
                if val not in (None, '', False):
                    has_val = True
                if f.required and _empty_value(val):
                    missing_required = True
            if not has_val or missing_required:
                continue
            child = existing[0] if existing else child_model()
            if not existing:
                _set_parent_child(child_model, form.model, child, instance)
                db.session.add(child)
            for fname, val in row.items():
                if hasattr(child, fname):
                    setattr(child, fname, val)
            continue
        by_ref = {}
        for i in existing:
            ref = item_ref(i, existing)
            if ref is not None:
                by_ref[str(ref)] = i
        rids = []
        seen = set()
        for k in form_data:
            if not k.startswith(prefix):
                continue
            rest = k[len(prefix):]
            if '_' not in rest:
                continue
            rid = rest.split('_', 1)[0]
            if rid not in seen:
                seen.add(rid)
                rids.append(rid)
        kept = set()
        for rid in rids:
            row = {}
            has_val = False
            missing_required = False
            for f in fields:
                val = _coerce_field_value(f, _field_raw(form_data, f'{prefix}{rid}_', f))
                row[f.name] = val
                if val not in (None, '', False):
                    has_val = True
                if f.required and _empty_value(val):
                    missing_required = True
            if not has_val or missing_required:
                continue
            child = by_ref.get(rid)
            if child is None:
                child = child_model()
                _set_parent_child(child_model, form.model, child, instance)
                db.session.add(child)
            for fname, val in row.items():
                if hasattr(child, fname):
                    setattr(child, fname, val)
            kept.add(rid)
        if session.get('single'):
            continue
        for i in existing:
            ref = item_ref(i, existing)
            if ref is None or str(ref) not in kept:
                db.session.delete(i)


def _expr_names(expr):
    return set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*', expr or ''))


def _aggregate_specs(form):
    """Campos do pai com `aggregate` dict (dos campos do form e da Entity)."""
    specs = []
    seen = set()
    for f in form._resolved_fields:
        if isinstance(f.aggregate, dict) and f.aggregate.get('table') and f.aggregate.get('sum'):
            specs.append((f.name, f.aggregate))
            seen.add(f.name)
    if form.module_name:
        try:
            mod = importlib.import_module(form.module_name)
        except ImportError:
            mod = None
        if mod:
            entidade = getattr(mod, 'Entity', {}) or {}
            key = form._child_entity_key(form.model, entidade) if form.model else None
            ent_cfg = entidade.get(key, {}) if key else {}
            if isinstance(ent_cfg, dict):
                for name, cfg in _entidade_fields(ent_cfg).items():
                    if name in seen or not isinstance(cfg, dict):
                        continue
                    agg = cfg.get('aggregate')
                    if isinstance(agg, dict) and agg.get('table') and agg.get('sum'):
                        specs.append((name, agg))
                        seen.add(name)
    return specs


def _apply_aggregates(form, instance):
    """Recomputa campos do pai com `aggregate` dict após salvar os filhos.

    Ex.: `'total': {'aggregate': {'table': 'items', 'sum': 'preco_unitario * quantidade'}}`.
    A expressão é avaliada por filho com namespace restrito aos atributos.
    """
    for name, agg in _aggregate_specs(form):
        if not hasattr(instance, name):
            continue
        table = agg.get('table')
        expr = agg.get('sum')
        rel = getattr(instance, table, None)
        if rel is None:
            total = 0
        else:
            children = rel.all() if hasattr(rel, 'all') and callable(rel.all) else list(rel)
            names = _expr_names(expr)
            total = 0
            for child in children:
                ns = {n: (getattr(child, n, None) or 0) for n in names}
                try:
                    total += float(eval(expr, {'__builtins__': {}}, ns))
                except Exception:
                    continue
        setattr(instance, name, round(total, 2))


def _session_items(instance, attr):
    """Materializa os itens de uma sessão a partir da relação/atributo."""
    raw = deep_attr(instance, attr) if instance is not None else None
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    if isinstance(raw, dict):
        return list(raw.values())
    all_ = getattr(raw, 'all', None)
    if callable(all_):
        return all_()
    return [raw]


def handle_form(form_spec, id=None, extra_ctx=None, instance=None):
    """Compat: delega ao orquestrador `core.do_form.do_form` (B2)."""
    from app.ajsystem.core.do_form import do_form
    return do_form(form_spec, id, extra_ctx, instance)
