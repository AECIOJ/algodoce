"""Motor da vitrine declarativa (Page type='showcase').

Resolve a config da showcase a partir do módulo, monta o contexto da página
(query de itens ativos com filtro por categoria, estado do carrinho de sessão,
config injetada na template) e os handlers das rotas geradas:

- `POST /<rota>/<id>/add|update|remove` — carrinho de sessão;
- `POST /<rota>/api/cliente` — identificação em memória (`session['client']`).

`/add` responde `401` quando há `client_fields` e a session ainda não tem o
cliente identificado (o JS abre o modal). Convenções: carrinho em
`session['cart_items']`, itens com `{entity}_id`/`quantidade`/`observacao`,
filtro de ativos por coluna `ativo`/`active` quando existir, imagem via
`adapter.get_uploads_endpoint()`.
"""
from flask import jsonify, request, session, url_for

from app.ajsystem.core.adapter import db, get_uploads_endpoint
from app.ajsystem.core.list import _resolve_model
from app.ajsystem.defs.page import resolve_max_width
from app.ajsystem.defs.showcase import (
    CART_SESSION_KEY,
    CLIENT_SESSION_KEY,
    SHOWCASE_LAYOUTS,
    resolve_client_fields,
    resolve_show,
    item_id_default,
)


def get_showcase(mod):
    """Config `Page['props']` do módulo (type='showcase'), ou `None`."""
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        if page.get('type') == 'showcase':
            return page.get('props') or {}
    return None


def get_page_max_width(mod):
    """`max_width` no nível do `Page` (página única), ou `None`.

    A vitrine dimensiona o layout proporcionalmente à largura da página; a
    largura é declarada no `Page`, não na config da showcase.
    """
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        return resolve_max_width(page.get('max_width'))
    return None


def _model_columns(model):
    table = getattr(model, '__table__', None)
    return getattr(table, 'columns', None) or {}


def _active_field(model):
    """Nome da coluna de ativo/desativado (`ativo`/`active`) ou `None`."""
    cols = _model_columns(model)
    for cand in ('ativo', 'active'):
        if cand in cols:
            return cand
    return None


def _fk_field_to(model, target_model):
    """Nome da coluna FK em `model` cujo alvo é `target_model`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or target_model is None:
        return None
    for rel in mapper.relationships.values():
        if getattr(rel, 'mapper', None) is not None and rel.mapper.class_ is target_model:
            for col in getattr(rel, 'local_columns', None) or []:
                return col.name
    return None


def _rel_for_column(model, column_name):
    """Nome da relationship cuja coluna local é `column_name`, ou `None`."""
    mapper = getattr(model, '__mapper__', None)
    if mapper is None or not column_name:
        return None
    for rel in mapper.relationships.values():
        for col in getattr(rel, 'local_columns', None) or []:
            if col.name == column_name:
                return rel.key
    return None


def _validate_show_fields(sc, model):
    """Valida que os campos de `show` existem na entidade/modelo."""
    cols = _model_columns(model)
    for campo, _pos in sc['show']:
        if campo not in cols:
            raise ValueError(
                f"SHOWCASE: campo {campo!r} de 'show' não existe em "
                f"{model.__name__}"
            )


def resolve_showcase(mod):
    """Resolve a config da showcase com modelos, campos e convenções prontos.

    Levanta `ValueError` em config inválida (falha rápida na montagem).
    """
    cfg = get_showcase(mod)
    if cfg is None:
        return None

    entity_name = cfg.get('fields')
    if not entity_name:
        raise ValueError("SHOWCASE: 'fields' (entidade dos itens) é obrigatório")
    model = _resolve_model(entity_name)
    sc = {
        'cfg': cfg,
        'entity': entity_name,
        'model': model,
        'item_id': item_id_default(entity_name),
        'layout': cfg.get('layout') or 'carousel',
        'show': resolve_show(cfg),
        'badge_id': cfg.get('badge_id'),
        'max_width': get_page_max_width(mod),
        'active_field': _active_field(model),
        'image_endpoint': get_uploads_endpoint(),
    }

    if sc['layout'] not in SHOWCASE_LAYOUTS:
        raise ValueError(
            f"SHOWCASE: layout inválido {sc['layout']!r} "
            f"(válidos: {', '.join(SHOWCASE_LAYOUTS)})"
        )

    _validate_show_fields(sc, model)

    ent_cfg = getattr(mod, 'Entity', {}) or {}
    fields_cfg = ent_cfg.get(entity_name) or {}
    if not isinstance(fields_cfg, dict):
        fields_cfg = {}

    def _is_image(campo):
        cfg = fields_cfg.get(campo)
        if isinstance(cfg, dict) and cfg.get('type') == 'IMAGE':
            return True
        return campo in ('imagem', 'image')

    image_field = next(
        (c for c, _pos in sc['show'] if _is_image(c)), None
    )
    sc['image_field'] = image_field
    sc['image_position'] = dict(sc['show']).get(image_field)

    filter_name = cfg.get('filter')
    filter_model = None
    filter_active = None
    if filter_name:
        filter_model = _resolve_model(filter_name)
        filter_active = _active_field(filter_model)
    sc['filter_entity'] = filter_name
    sc['filter_model'] = filter_model
    sc['filter_active_field'] = filter_active
    sc['category_field'] = _fk_field_to(model, filter_model) if filter_model else None
    sc['category_rel'] = _rel_for_column(model, sc['category_field'])

    client_fields = resolve_client_fields(cfg.get('client_fields'))
    sc['client_fields'] = client_fields
    sc['session_key'] = CART_SESSION_KEY
    sc['client_session_key'] = CLIENT_SESSION_KEY
    return sc


def _map_produto(sc, produto, itens_qtd):
    """Mapeia um item da entidade p/ o dict consumido pela template.

    Chaves por posição (`title`, `left`, `right`, `qty`), `id`, `categoria`,
    `image_url` (quando houver imagem) e `fields` (campo → valor) para os
    demais layouts. `qty` vira o mínimo (default 1).
    """
    d = {'id': produto.id, 'fields': {}}
    d['categoria'] = (
        getattr(produto, sc['category_field'], None)
        if sc['category_field'] else None
    )
    d['qtd_orcamento'] = itens_qtd.get(produto.id, '')
    image_field = sc['image_field']
    for campo, pos in sc['show']:
        val = getattr(produto, campo, None)
        d['fields'][campo] = val
        if pos == 'qty':
            d['qty'] = int(val or 1)
        else:
            d[pos] = val
    if image_field:
        val = d['fields'].get(image_field)
        d['image_url'] = url_for(sc['image_endpoint'], filename=val) if val else None
        d['image_field'] = image_field
        d['image_position'] = sc['image_position']
    return d


def _categorias(sc):
    query = sc['filter_model'].query
    if sc['filter_active_field']:
        query = query.filter(
            getattr(sc['filter_model'], sc['filter_active_field']) == True
        )
    if hasattr(sc['filter_model'], 'ordem'):
        query = query.order_by(sc['filter_model'].ordem)
    elif hasattr(sc['filter_model'], 'nome'):
        query = query.order_by(sc['filter_model'].nome)
    return query.all()


def showcase_context(mod):
    """Contexto da página da vitrine (chamado por `do_page`)."""
    sc = resolve_showcase(mod)
    if sc is None:
        return None
    model = sc['model']

    filter_param = (sc['filter_entity'] or 'categoria').lower()
    categoria_id = request.args.get(filter_param, type=int)

    query = model.query
    if sc['active_field']:
        query = query.filter(getattr(model, sc['active_field']) == True)
    if sc['filter_model'] and sc['category_rel'] and sc['category_field']:
        fk = getattr(model, sc['category_field'])
        rel = getattr(model, sc['category_rel'])
        if sc['filter_active_field']:
            query = query.filter(
                db.or_(
                    fk == None,
                    rel.has(getattr(sc['filter_model'], sc['filter_active_field']) == True),
                )
            )
    if categoria_id and sc['category_field']:
        query = query.filter(getattr(model, sc['category_field']) == categoria_id)
    produtos = query.all()

    categorias = _categorias(sc) if sc['filter_model'] else []

    items = session.get(sc['session_key'], [])
    itens_qtd = {i.get(sc['item_id']): i.get('quantidade') for i in items}

    bp = request.endpoint.rsplit('.', 1)[0] if request.endpoint else ''
    identify_url = url_for(f'{bp}.identificar') if sc['client_fields'] else None
    return {
        'showcase': sc,
        'produtos': [_map_produto(sc, p, itens_qtd) for p in produtos],
        'categorias': [
            {'id': c.id, 'nome': getattr(c, 'nome', str(c.id))} for c in categorias
        ],
        'categoria_id': categoria_id,
        'filter_param': filter_param,
        'total_itens': len(items),
        'itens_qtd': itens_qtd,
        'base_url': request.path.rstrip('/'),
        'identify_url': identify_url,
        'client_fields': sc['client_fields'],
        'list_url': url_for(request.endpoint) if request.endpoint else request.path,
    }


def make_add(sc):
    """Handler gerado de `POST /<rota>/<id>/add` (carrinho de sessão)."""
    model = sc['model']
    item_id = sc['item_id']

    def add(id):
        produto = model.query.get_or_404(id)
        data = request.get_json(silent=True) or {}
        quantidade = int(data.get('quantidade', 1))
        observacao = data.get('observacao', '')

        if sc['client_fields'] and not session.get(sc['client_session_key']):
            return jsonify(error='identificar'), 401

        for campo, pos in sc['show']:
            if pos == 'qty':
                minima = int(getattr(produto, campo, None) or 1)
                if quantidade < minima:
                    titulo = next(
                        (getattr(produto, c, None) for c, p in sc['show'] if p == 'title'),
                        str(id),
                    )
                    return jsonify(
                        error=f'A quantidade mínima para {titulo} é {minima} und.'
                    ), 400
                break

        items = session.get(sc['session_key'], [])
        found = False
        for i in items:
            if i.get(item_id) == id:
                i['quantidade'] += quantidade
                if observacao:
                    i['observacao'] = observacao
                found = True
                break
        if not found:
            items.append({
                item_id: id,
                'quantidade': quantidade,
                'observacao': observacao or None,
            })
        session[sc['session_key']] = items
        return jsonify(success=True, total_itens=len(items))

    return add


def make_update(sc):
    """Handler gerado de `POST /<rota>/<id>/update`.

    Valida quantidade ≥ mínimo (mesma regra do `add`) e produto existente —
    respostas 400/404 em vez de gravar estado inválido na session.
    """
    model = sc['model']
    item_id = sc['item_id']

    def update(id):
        produto = model.query.get_or_404(id)
        data = request.get_json(silent=True) or {}

        min_field = next(
            (c for c, p in sc['show'] if p == 'qty'), None
        )
        minima = int(getattr(produto, min_field, None) or 1) if min_field else 1

        if 'quantidade' in data:
            try:
                quantidade = int(data['quantidade'])
            except (TypeError, ValueError):
                return jsonify(error='Quantidade inválida.'), 400
            if quantidade < minima:
                titulo = next(
                    (getattr(produto, c, None) for c, p in sc['show'] if p == 'title'),
                    str(id),
                )
                return jsonify(
                    error=f'A quantidade mínima para {titulo} é {minima} und.'
                ), 400
        else:
            quantidade = None

        observacao = data.get('observacao')
        items = session.get(sc['session_key'], [])
        for i in items:
            if i.get(item_id) == id:
                if quantidade is not None:
                    i['quantidade'] = quantidade
                if observacao is not None:
                    i['observacao'] = observacao.strip() or None
                break
        session[sc['session_key']] = items
        return jsonify(success=True, total_itens=len(items))

    return update


def make_remove(sc):
    """Handler gerado de `POST /<rota>/<id>/remove`."""
    item_id = sc['item_id']

    def remove(id):
        items = session.get(sc['session_key'], [])
        session[sc['session_key']] = [
            i for i in items if i.get(item_id) != id
        ]
        return jsonify(success=True, total_itens=len(session[sc['session_key']]))

    return remove


def make_identify(sc):
    """Handler gerado de `POST /<rota>/api/cliente` (identificação em memória).

    Valida os campos obrigatórios e guarda os valores na session sob
    `session['client']` — sem persistir em banco.
    """
    def identify():
        data = request.get_json(silent=True) or {}
        payload = {}
        for f in sc['client_fields']:
            val = data.get(f['token'], '').strip()
            if f['required'] and not val:
                return jsonify(error=f'{f["label"]} é obrigatório'), 400
            payload[f['token']] = val
        session[sc['client_session_key']] = payload
        return jsonify(success=True)

    return identify


def generated_routes(mod):
    """Rotas da vitrine a gerar: lista de (rule, endpoint, func, methods).

    Vazio quando o módulo não é showcase. Os endpoints (`adicionar`,
    `atualizar`, `remover`, `identificar`) são sobrescritos se o módulo os
    declarar com `@auto.rota`.
    """
    sc = resolve_showcase(mod)
    if sc is None:
        return []
    routes = [
        ('/<int:id>/add', 'adicionar', make_add(sc), ['POST']),
        ('/<int:id>/update', 'atualizar', make_update(sc), ['POST']),
        ('/<int:id>/remove', 'remover', make_remove(sc), ['POST']),
    ]
    if sc['client_fields']:
        routes.append(('/api/cliente', 'identificar', make_identify(sc), ['POST']))
    return routes
