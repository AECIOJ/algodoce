"""Geração automática de blueprints CRUD a partir da definição do módulo.

Modo declarativo (padrão-alvo): o módulo de rotas declara apenas `Entity` +
`List` (+ `Form` opcional) e, para rotas custom, usa o decorator `@auto.rota`.
NÃO declara `bp = Blueprint(...)` nem `@bp.route`. O motor:

- cria o blueprint internamente a partir do nome do arquivo (slug normalizado);
- monta as rotas CRUD padrão (listagem, formulário e, se configurado em `Form`,
  exclusão e ativar/desativar);
- monta as rotas custom declaradas com `@auto.rota`;
- registra o blueprint no app (via `registrar_modulos`, conforme o menu).

Modos legados: módulos que ainda expõem `bp = Blueprint(...)` são preservados —
o motor retorna o bp existente e estes continuam registrados explicitamente.
"""
import importlib
import unicodedata
from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import login_required

from app.ajsystem.core.adapter import db
from app.ajsystem.core.do_list import do_list
from app.ajsystem.core.form import handle_form, _resolve_delete, _when_allows, _resolve_label
from app.ajsystem.core.do_page import do_page
from app.ajsystem.core.showcase import generated_routes as _generated_showcase_routes

# registro de rotas custom declaradas com @auto.rota, indexado por nome de módulo
_ROTAS = {}


def _normalizar_slug(label: str) -> str:
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def rota(path, methods=None, endpoint=None, defaults=None):
    """Decorator para declarar rotas custom sem um objeto Blueprint.

    No momento do import do módulo ele apenas registra a view no motor; o bp é
    montado depois por `montar_blueprint`. O `endpoint` default é o nome da
    função (`list`, `toggle`, `search`, ...) e define o endpoint da rota.
    """
    methods = methods or ['GET']

    def _decorator(func):
        mod_name = func.__module__
        _ROTAS.setdefault(mod_name, []).append({
            'path': path,
            'methods': methods,
            'endpoint': endpoint or func.__name__,
            'defaults': defaults,
            'func': func,
        })
        return func

    return _decorator


def _rotas_do_modulo(mod):
    return _ROTAS.get(mod.__name__, []) if mod is not None else []


def _blueprint_no_modulo(mod):
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
    return None


def _entidade_principal(mod):
    form = _form_config(mod)
    if form:
        fields = form.get('fields')
        if isinstance(fields, str) and fields in getattr(mod, 'Entity', {}):
            return fields
    lista = _lista_config(mod)
    if isinstance(lista, dict):
        fields = lista.get('fields')
        if isinstance(fields, str):
            return fields if fields in getattr(mod, 'Entity', {}) else None
        columns = fields or [next(iter(getattr(mod, 'Entity', {})), '')]
        if columns:
            primeira = columns[0]
            entidade = primeira.split('.', 1)[0] if isinstance(primeira, str) else ''
            if entidade in getattr(mod, 'Entity', {}):
                return entidade
    entidades = getattr(mod, 'Entity', {})
    if entidades:
        return next(iter(entidades))
    return None


def _get_model(mod):
    entidade = _entidade_principal(mod)
    if entidade:
        cand = getattr(mod, entidade, None)
        if isinstance(cand, type):
            return cand
    form = _form_config(mod)
    if isinstance(form.get('model'), type):
        return form['model']
    return None


def _form_config(mod):
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        props = page.get('props') or {}
        f = props.get('form')
        if isinstance(f, dict):
            return f
    f = getattr(mod, 'Form', None)
    return f if isinstance(f, dict) else {}


def _lista_config(mod):
    """Config do `List`: props.list de Page (novo) ou aba List em props.tabs."""
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        props = page.get('props') or {}
        list_cfg = props.get('list')
        if isinstance(list_cfg, dict):
            return list_cfg
        tabs = props.get('tabs') or page.get('tabs') or {}
        for key, cfg in tabs.items():
            if isinstance(cfg, dict) and cfg.get('type', 'Custom') == 'List':
                cfg = dict(cfg)
                for std in ('type', 'max_width', 'template'):
                    cfg.pop(std, None)
                return cfg
    lista = getattr(mod, 'List', None)
    return lista if isinstance(lista, dict) else None


def _toggle_field(form_cfg):
    """Campo booleano do toggle: `Form['toggle']` explícito ou derivado do
    botão `on_off` em `Form['buttons']` (default 'ativo')."""
    if form_cfg.get('toggle'):
        return form_cfg['toggle']
    for b in form_cfg.get('buttons') or []:
        if b == 'on_off':
            return 'ativo'
        if isinstance(b, dict) and len(b) == 1 and 'on_off' in b:
            overrides = b['on_off'] or {}
            return overrides.get('field') or 'ativo'
        if isinstance(b, dict) and b.get('on_off') is True and b.get('field'):
            return b['field']
    return None


def _page_single(mod):
    """True quando o módulo NÃO é crud (type != 'crud' ou tabs vazio legado)."""
    page = getattr(mod, 'Page', None)
    if not isinstance(page, dict):
        return False
    page_type = page.get('type')
    if page_type is not None:
        return page_type != 'crud'
    return bool('tabs' in page and not page.get('tabs'))


def _generated_crud(mod, slug):
    """Retorna as rotas CRUD padrão a gerar: lista de (rule, endpoint, func).

    Módulos com `type != 'crud'` no `Page` e módulos legados com
    `CRUD = False` não geram rotas CRUD — apenas as declaradas com
    `@auto.rota` (e a `list` via `do_page`).
    """
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        page_type = page.get('type', 'crud')
        if page_type != 'crud':
            return []
        if page.get('crud') is False:
            return []
    if getattr(mod, 'CRUD', True) is False:
        return []
    entidade = _entidade_principal(mod)
    model = _get_model(mod)
    form_cfg = _form_config(mod)
    routes = []

    def _list():
        return do_list(entidade, mod.__name__)
    routes.append(('/', 'list', _list))

    def _form(id=None):
        spec = dict(_form_config(mod) or _lista_config(mod) or {})
        spec.setdefault('module_name', mod.__name__)
        extra = None
        pre_get = spec.pop('pre_get', None)
        if callable(pre_get):
            extra = pre_get(mod, id)
        return handle_form(spec, id, extra_ctx=extra)
    routes.append(('/novo', 'form', _form))
    routes.append(('/<int:id>/editar', 'form', _form))

    del_cfg = _resolve_delete(
        form_cfg.get('delete'),
        form_cfg.get('delete_when'),
        form_cfg.get('flash_deny'),
        form_cfg.get('flash_excluido'),
        label=_resolve_label(mod, _entidade_principal(mod)),
    )
    if model is not None and del_cfg:
        def _delete(id):
            instance = model.query.get_or_404(id)
            if not _when_allows(del_cfg['when'], instance):
                flash(del_cfg['msg_no'], 'danger')
                return redirect(url_for(f'{slug}.form', id=id))
            db.session.delete(instance)
            db.session.commit()
            flash(del_cfg['msg_ok'], 'success')
            return redirect(url_for(f'{slug}.list'))
        routes.append(('/<int:id>/excluir', 'delete', _delete))

    campo = _toggle_field(form_cfg)
    if model is not None and campo:
        flash_toggle = form_cfg.get('flash_toggle') or 'Atualizado!'

        def _toggle(id):
            instance = model.query.get_or_404(id)
            setattr(instance, campo, not getattr(instance, campo))
            db.session.commit()
            flash(flash_toggle, 'success')
            return redirect(url_for(f'{slug}.form', id=id))
        routes.append(('/<int:id>/toggle', 'toggle', _toggle))

    return routes


def montar_blueprint(mod, slug=None, url_prefix=None, login=True, label=None):
    """Resolve o Blueprint de um módulo.

    - módulo com `bp` próprio (legado) → retorna existente, sem alterar;
    - módulo declarativo → cria o bp, monta as CRUD geradas (a menos que o
      endpoint seja declarado com `@auto.rota`, o módulo declare `crud: False`
      no `Page` ou `CRUD = False`) + as rotas custom, injeta `mod.bp` e retorna.

    Módulos públicos passam `login=False` (sem `login_required` no blueprint).
    """
    existente = _blueprint_no_modulo(mod)
    if existente is not None:
        return existente

    if label:
        setattr(mod, '_label', label)

    if not slug:
        slug = _normalizar_slug(mod.__name__.rsplit('.', 1)[-1])
    prefix = url_prefix or f"/{slug}"

    bp = Blueprint(slug, mod.__name__, url_prefix=prefix)

    if login:
        @bp.before_request
        @login_required
        def protect():
            pass

    custom = _rotas_do_modulo(mod)
    custom_names = {r['endpoint'] for r in custom}

    # rotas custom declaradas
    for r in custom:
        kwargs = {'methods': r['methods']}
        if r['defaults']:
            kwargs['defaults'] = r['defaults']
        bp.add_url_rule(
            r['path'], r['endpoint'], r['func'], **kwargs,
        )

    # rotas CRUD geradas (somente quando o endpoint não for declarado)
    generated = _generated_crud(mod, slug)
    for rule, endpoint, func in generated:
        if endpoint in custom_names:
            continue
        methods = ('GET', 'POST') if endpoint in ('novo', 'form') else ('POST',) if endpoint == 'delete' else ('GET',)
        kwargs = {}
        if rule == '/novo':
            kwargs['defaults'] = {'id': None}
        bp.add_url_rule(rule, endpoint, func, methods=methods, **kwargs)

    # vitrine declarativa (Page type='showcase') — carrinho + identificação
    for rule, endpoint, func, methods in _generated_showcase_routes(mod):
        if endpoint in custom_names:
            continue
        bp.add_url_rule(rule, endpoint, func, methods=methods)

    # página única (sem CRUD nem rota `list` custom) → `list` renderiza via do_page
    if _page_single(mod) and 'list' not in custom_names:
        bp.add_url_rule('/', 'list', lambda: do_page(mod), methods=['GET'], strict_slashes=False)

    setattr(mod, 'bp', bp)
    return bp


def _iterar_itens_menus(modulo_menu):
    """Percorre a árvore de menus produzindo pares (label, item)."""
    for label, item in modulo_menu.items():
        if item.submenus:
            yield from _iterar_itens_menus(item.submenus)
        yield label, item


def _blueprint_construcao(slug, label=None, login=True):
    """Blueprint genérico para módulo ainda não migrado (página em construção).

    Toda URL do blueprint renderiza o template `pages/construcao.html` com o
    rótulo do item de menu, evitando 404 enquanto a página não existe no `sys`.
    """
    bp = Blueprint(slug, f'{__name__}.{slug}', url_prefix=f'/{slug}')

    if login:
        @bp.before_request
        @login_required
        def protect():
            pass

    def _construcao():
        return render_template('pages/construcao.html', pagina=label or slug)

    bp.add_url_rule('/', 'list', _construcao, methods=['GET'], strict_slashes=False)
    bp.add_url_rule('/novo', 'form', _construcao)
    bp.add_url_rule('/<int:id>/editar', 'form', _construcao)
    return bp


def registrar_modulos(app, modulo_menu, modulo_ini='app.routes.sys', login=True):
    """Itera a árvore de menus e registra blueprints (auto-gerados ou existentes).

    Para cada submenu/item, deriva o slug (do `endpoint` explícito quando houver,
    senão do rótulo normalizado) e importa o módulo. Módulo que já expõe `bp` é
    ignorado (registrado explicitamente na app). Módulo sem bp tem o CRUD montado
    e é registrado. Itens com `url` explícita são ignorados.

    `login=False` registra módulos públicos. Módulos do pacote `.site` recebem
    blueprint nomeado `site_<slug>` (prefixo `/site_` evita colisão com módulos
    de mesmo nome em `.sys`, ex.: `produtos`). O prefixo de URL é o `route`
    declarado no `Page` quando houver; senão `/{slug}`, com fallback para
    `/site/{slug}` se esse caminho já estiver em uso (rota existente).
    """
    registrados = []
    vistos = set()
    para_site = modulo_ini.endswith('.site')
    for label, item in _iterar_itens_menus(modulo_menu):
        if item.url:
            continue
        slug = _normalizar_slug(item.page or label)
        if slug in vistos:
            continue
        try:
            mod = importlib.import_module(f'{modulo_ini}.{slug}')
        except ImportError:
            vistos.add(slug)
            bp = _blueprint_construcao(slug, label=label, login=login)
            if bp is not None:
                app.register_blueprint(bp)
                registrados.append(bp.name)
            continue
        if _blueprint_no_modulo(mod) is not None:
            continue
        if para_site:
            page_cfg = getattr(mod, 'Page', None)
            route = page_cfg.get('route') if isinstance(page_cfg, dict) else None
            base = _normalizar_slug(route) if route is not None else slug
            prefix = f'/{base}'
            if not route and any(r.rule == f'/{base}/' for r in app.url_map.iter_rules()):
                prefix = f'/site{prefix}'
            bp = montar_blueprint(mod, slug=f'site_{slug}', url_prefix=prefix, label=label, login=login)
        else:
            bp = montar_blueprint(mod, slug, label=label, login=login)
        if bp is None:
            continue
        app.register_blueprint(bp)
        registrados.append(bp.name)

    # ── rotas automáticas do site (quando não existem módulos root/sistema) ──
    if para_site:
        _registrar_rotas_automaticas(app)

    return registrados


def _registrar_rotas_automaticas(app):
    """Gera rotas automáticas para o site público que não dependem de módulos.

    - ``/``  → redirect para ``/sobre`` (público) ou ``/sistema`` (logado)
    - ``/sistema`` → ``pages/construcao.html`` (``login_required``)
    """
    from flask import redirect as flask_redirect, render_template
    from flask_login import login_required, current_user

    # Não registra se já existir rota na raiz
    has_root = any(r.rule == '/' for r in app.url_map.iter_rules())
    if not has_root:
        @app.route('/')
        def _site_root():
            if current_user.is_authenticated:
                return flask_redirect('/sistema')
            return flask_redirect('/sobre')

    # Não registra se já existir rota /sistema
    has_sistema = any(r.rule == '/sistema' for r in app.url_map.iter_rules())
    if not has_sistema:
        @app.route('/sistema')
        @login_required
        def _site_sistema():
            return render_template('pages/construcao.html')