"""Motor do carrinho declarativo (Page type='cart').

Resolve a config a partir do módulo, deriva as entidades/relações a partir da
sessão `table` (pai, origem, item_id, mínimo), monta o contexto da página e o
fluxo de envio (cria pai + itens + registro `form`, dispara `on_send`
pós-commit, confirma com flash + redirect).

Derivações das FKs do modelo da sessão `table`:
- FK cujo alvo tem relação de volta (ONETOMANY/ONETOONE) para o modelo → pai
  (entidade principal, ex.: `Quote`); a FK da sessão `form` que aponta para o
  pai é preenchida automaticamente;
- FK restante → origem dos itens (ex.: `Product`); o nome da coluna é o
  `item_id` (`product_id`);
- mínimo de quantidade = coluna `qtd_minima` da origem (default 1).
"""
from datetime import datetime, timezone

from flask import flash, jsonify, redirect, request, session, url_for

from ajsystem.core.adapter import db
from ajsystem.core.list import _resolve_model
from ajsystem.defs.cart import (
    CART_CONFIRM_FLASH,
    CART_MORE_ITEMS_LINK,
    CART_SESSION_KEY,
    CART_TITLE,
    CLIENT_SESSION_KEY,
    field_prefix,
    resolve_sessions,
)
from ajsystem.defs.data import build_field_config
from ajsystem.defs.data import resolve_max_width


def get_cart(mod):
    """Config `Page['props']` do módulo (type='cart'), ou `None`."""
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        if page.get('type') == 'cart':
            return page.get('props') or {}
    return None


def get_on_send(mod):
    """Evento `Page['props']['on_send']` (callable) ou `None`."""
    page = getattr(mod, 'Page', None)
    if not isinstance(page, dict):
        return None
    props = page.get('props') or {}
    on_send = props.get('on_send')
    if isinstance(on_send, str):
        on_send = getattr(mod, on_send, None)
    return on_send if callable(on_send) else None


def _columns(model):
    table = getattr(model, '__table__', None)
    return getattr(table, 'columns', None) or {}


def _fk_columns(model):
    """Colunas com FK do modelo, em ordem."""
    cols = _columns(model)
    return [c.name for c in cols.values() if c.foreign_keys]


def _fk_target(model, column_name):
    """Modelo alvo da FK `column_name`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or not column_name:
        return None
    for rel in mapper.relationships.values():
        for col in getattr(rel, 'local_columns', None) or []:
            if col.name == column_name:
                return rel.mapper.class_
    return None


def _has_back_rel(model, target):
    """True quando `model` tem relação de volta (uselist ou não) p/ `target`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None:
        return False
    for rel in mapper.relationships.values():
        try:
            if rel.mapper.class_ is target:
                return True
        except Exception:
            continue
    return False


def _parent_fk_column(model, parent_model):
    """Coluna FK de `model` que aponta para `parent_model`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or parent_model is None:
        return None
    for rel in mapper.relationships.values():
        if getattr(rel, 'mapper', None) is not None and rel.mapper.class_ is parent_model:
            for col in getattr(rel, 'local_columns', None) or []:
                return col.name
    return None


def _first_session(sc, stype):
    return next((s for s in sc['sessions'] if s['type'] == stype), None)


def resolve_cart(mod):
    """Resolve `Page['cart']` com modelos, derivações e convenções prontos.

    Levanta `ValueError` em config inválida (falha rápida na montagem).
    Retorna `None` quando o módulo não é um carrinho.
    """
    cfg = get_cart(mod)
    if cfg is None:
        return None
    sessions_raw = resolve_sessions(cfg)

    sc = {
        'cfg': cfg,
        'sessions': [],
        'parent_entity': None,
        'parent_model': None,
        'origin_entity': None,
        'origin_model': None,
        'item_id': None,
        'min_field': 'qtd_minima',
        'session_key': CART_SESSION_KEY,
        'client_session_key': CLIENT_SESSION_KEY,
        'more_items_link': CART_MORE_ITEMS_LINK,
        'title': CART_TITLE,
    }

    for s in sessions_raw:
        sc['sessions'].append({**s, 'model': _resolve_model(s['fields'])})

    table = _first_session(sc, 'table')
    if table is None:
        raise ValueError("CART: uma sessão 'table' (itens) é obrigatória")
    if len([s for s in sc['sessions'] if s['type'] == 'table']) != 1:
        raise ValueError("CART: exatamente uma sessão 'table' é suportada")

    tmodel = table['model']
    fks = _fk_columns(tmodel)
    parents = [c for c in fks if _has_back_rel(_fk_target(tmodel, c), tmodel)]
    if len(parents) != 1:
        raise ValueError(
            f"CART: {table['fields']} precisa de exatamente uma FK pai "
            f"(encontradas: {len(parents)} em {fks})"
        )
    parent_col = parents[0]
    parent_model = _fk_target(tmodel, parent_col)
    origin_cols = [c for c in fks if c != parent_col]
    if len(origin_cols) != 1:
        raise ValueError(
            f"CART: {table['fields']} precisa de exatamente uma FK de origem "
            f"(além do pai), encontradas: {len(origin_cols)} em {fks}"
        )
    origin_col = origin_cols[0]
    origin_model = _fk_target(tmodel, origin_col)

    sc['parent_entity'] = parent_model.__name__
    sc['parent_model'] = parent_model
    sc['origin_entity'] = origin_model.__name__
    sc['origin_model'] = origin_model
    sc['item_id'] = origin_col

    for s in sc['sessions']:
        s['prefix'] = field_prefix(s['fields'])
        s['parent_fk'] = _parent_fk_column(s['model'], parent_model)

    forms = [s for s in sc['sessions'] if s['type'] == 'form']
    if len(forms) > 1:
        raise ValueError("CART: no máximo uma sessão 'form' é suportada")
    return sc


def _session_items(sc):
    """Itens do carrinho resolvidos com o produto de origem (memória)."""
    origin = sc['origin_model']
    item_id = sc['item_id']
    out = []
    for i in session.get(sc['session_key'], []):
        obj = origin.query.get(i.get(item_id))
        if obj is None:
            continue
        out.append({
            'item_id': i.get(item_id),
            'produto': obj,
            'quantidade': i.get('quantidade'),
            'observacao': i.get('observacao') or '',
            'qtd_minima': minimo_quantidade(sc, obj),
        })
    return out


def _form_fields(sc, mod, session):
    """Campos de uma sessão `form` resolvidos para render (inputs + label).

    Usa o `Entity` do módulo (tipos/options) validando contra as colunas do
    modelo. A FK que aponta para o pai é ignorada (gerida pelo motor).
    """
    ent_cfg = getattr(mod, 'Entity', {}) or {}
    fields_cfg = ent_cfg.get(session['fields']) or {}
    if not isinstance(fields_cfg, dict):
        fields_cfg = {}
    cols = _columns(session['model'])
    result = []
    for name, cfg in fields_cfg.items():
        if name.startswith('__'):
            continue
        if name == session['parent_fk']:
            continue
        if name not in cols:
            raise ValueError(
                f"CART: campo {name!r} de {session['fields']!r} não existe "
                f"em {session['model'].__name__}"
            )
        fc = build_field_config(name, cfg)
        result.append({
            'name': name,
            'input_name': f"{session['prefix']}{name}",
            'label': fc.get('label') or name,
            'input': fc.get('input') or 'text',
            'options': fc.get('options'),
            'required': bool(fc.get('required')),
        })
    return result


def cart_context(mod):
    """Contexto da página do carrinho (chamado por `do_page`)."""
    sc = resolve_cart(mod)
    if sc is None:
        return None
    form_session = _first_session(sc, 'form')
    form_sessions = []
    if form_session is not None:
        form_sessions.append({
            'key': form_session['key'],
            'label': form_session['label'],
            'fields': _form_fields(sc, mod, form_session),
        })
    items = _session_items(sc)
    page = getattr(mod, 'Page', {}) or {}
    max_width = resolve_max_width(page.get('max_width'))
    return {
        'cart': sc,
        'cart_title': sc['title'],
        'max_width': max_width,
        'cliente': session.get(sc['client_session_key']),
        'items': items,
        'form_sessions': form_sessions,
        'more_items_link': sc['more_items_link'],
        'base_url': request.path.rstrip('/'),
    }


def _convert(tname, raw):
    """Converte o valor bruto do form conforme o tipo da coluna do modelo."""
    if raw is None or raw == '':
        return None
    if 'DateTime' in tname:
        return datetime.strptime(raw, '%Y-%m-%dT%H:%M')
    if 'Date' in tname:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    if 'Time' in tname:
        return datetime.strptime(raw, '%H:%M').time()
    if tname in ('Integer', 'SmallInteger', 'BigInteger'):
        return int(raw)
    return raw


def _make_event(sc, mod, quote):
    """Cria o registro da sessão `form` (ex.: Event) a partir do `request.form`.

    Retorna `None` quando o carrinho não declara sessão `form`.
    """
    form_session = _first_session(sc, 'form')
    if form_session is None:
        return None
    model = form_session['model']
    instance = model()
    if form_session['parent_fk']:
        setattr(instance, form_session['parent_fk'], quote.id)
    cols = _columns(model)
    for f in _form_fields(sc, mod, form_session):
        raw = request.form.get(f['input_name'])
        col = cols.get(f['name'])
        tname = col.type.__class__.__name__ if col is not None else ''
        setattr(instance, f['name'], _convert(tname, raw))
    db.session.add(instance)
    return instance


def send_cart(mod):
    """Fluxo de envio do carrinho (criar + persistir + confirmar).

    Cria o pai + os itens da sessão `table` + o registro da sessão `form`,
    faz o commit, dispara `Page['on_send'](pai)` (pós-commit) e confirma com
    flash + redirect para a listagem do módulo. Retorna a resposta Flask.
    """
    sc = resolve_cart(mod)
    cliente = session.get(sc['client_session_key'])
    if not cliente:
        return redirect(url_for(f'{_bp()}.list'))
    session_items = session.get(sc['session_key'], [])
    if not session_items:
        return redirect(url_for(f'{_bp()}.list'))

    quote = sc['parent_model'](
        cliente_nome=cliente.get('nome'),
        cliente_telefone=cliente.get('telefone'),
        data_pedido=datetime.now(timezone.utc),
    )
    db.session.add(quote)
    db.session.flush()

    table = _first_session(sc, 'table')
    tmodel = table['model']
    item_id = sc['item_id']
    for i in session_items:
        t = tmodel(
            **{table['parent_fk']: quote.id},
            **{item_id: i.get(item_id)},
            quantidade=i.get('quantidade'),
            observacao=i.get('observacao') or None,
        )
        db.session.add(t)

    _make_event(sc, mod, quote)

    db.session.commit()

    on_send = get_on_send(mod)
    if on_send is not None:
        try:
            on_send(quote)
        except Exception:
            # pós-commit: falha no handler não deve falhar o envio.
            pass

    flash(CART_CONFIRM_FLASH, 'success')
    return redirect(url_for(f'{_bp()}.list'))


def _bp():
    """Nome do blueprint a partir do endpoint atual (ex.: `site_orcamento`)."""
    return request.endpoint.rsplit('.', 1)[0] if request.endpoint else ''


def minimo_quantidade(sc, obj):
    """Quantidade mínima de um item de origem (coluna `min_field`, default 1)."""
    field = sc.get('min_field')
    if field and hasattr(obj, field):
        val = getattr(obj, field, None)
        if val is not None:
            return int(val)
    return 1


def count_items(sc):
    """Total de itens no carrinho (para o endpoint de contagem)."""
    return len(session.get(sc['session_key'], []))
