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
from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required

from app.ajsystem.app_config import db
from app.ajsystem.engine.handle_list import render_list
from app.ajsystem.form import handle_form, _resolve_delete, _when_allows, _resolve_label

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
    form = getattr(mod, 'Form', None)
    if isinstance(form, dict):
        fields = form.get('fields')
        if isinstance(fields, str) and fields in getattr(mod, 'Entity', {}):
            return fields
    lista = getattr(mod, 'List', None)
    if isinstance(lista, dict):
        columns = lista.get('columns') or [next(iter(getattr(mod, 'Entity', {})), '')]
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
    form = getattr(mod, 'Form', None)
    if isinstance(form, dict) and isinstance(form.get('model'), type):
        return form['model']
    return None


def _form_config(mod):
    f = getattr(mod, 'Form', None)
    return f if isinstance(f, dict) else {}


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


def _generated_crud(mod, slug):
    """Retorna as rotas CRUD padrão a gerar: lista de (rule, endpoint, func)."""
    entidade = _entidade_principal(mod)
    model = _get_model(mod)
    form_cfg = _form_config(mod)
    routes = []

    def _list():
        return render_list(entidade, mod.__name__)
    routes.append(('/', 'list', _list))

    def _form(id=None):
        spec = dict(getattr(mod, 'Form') or getattr(mod, 'List') or {})
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
      endpoint seja declarado com `@auto.rota`) + as rotas custom, injeta
      `mod.bp` e retorna.
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
    for rule, endpoint, func in _generated_crud(mod, slug):
        if endpoint in custom_names:
            continue
        methods = ('GET', 'POST') if endpoint in ('novo', 'form') else ('POST',) if endpoint == 'delete' else ('GET',)
        kwargs = {}
        if rule == '/novo':
            kwargs['defaults'] = {'id': None}
        bp.add_url_rule(rule, endpoint, func, methods=methods, **kwargs)

    setattr(mod, 'bp', bp)
    return bp


def _iterar_itens_menus(modulo_menu):
    """Percorre a árvore de menus produzindo pares (label, item)."""
    for label, item in modulo_menu.items():
        if not isinstance(item, dict):
            continue
        if item.get('submenus'):
            yield from _iterar_itens_menus(item['submenus'])
        yield label, item


def registrar_modulos(app, modulo_menu, modulo_ini='app.routes.sys'):
    """Itera a árvore de menus e registra blueprints (auto-gerados ou existentes).

    Para cada submenu/item, deriva o slug (do `endpoint` explícito quando houver,
    senão do rótulo normalizado) e importa o módulo. Módulo que já expõe `bp` é
    ignorado (registrado explicitamente na app). Módulo sem bp tem o CRUD montado
    e é registrado. Itens com `url` explícita são ignorados.
    """
    registrados = []
    vistos = set()
    for label, item in _iterar_itens_menus(modulo_menu):
        if 'url' in item:
            continue
        if item.get('endpoint'):
            slug = _normalizar_slug(item['endpoint'].split('.')[0])
        else:
            slug = _normalizar_slug(label)
        if slug in vistos:
            continue
        try:
            mod = importlib.import_module(f'{modulo_ini}.{slug}')
        except ImportError:
            continue
        vistos.add(slug)
        if _blueprint_no_modulo(mod) is not None:
            continue
        bp = montar_blueprint(mod, slug, label=label)
        if bp is None:
            continue
        app.register_blueprint(bp)
        registrados.append(bp.name)
    return registrados