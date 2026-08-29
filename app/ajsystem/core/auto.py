"""AUTO — montagem de blueprints a partir do menu do config.

Reescrito do zero observando `core/old/auto.py`. Para cada item de menu importa
o módulo de rota e, se declarativo (`Page`/`Schema`), monta o blueprint CRUD
via `core.do_list`/`core.do_form`. Módulos ausentes → `pages/construcao.html`.
"""
import importlib
import unicodedata
from dataclasses import fields as dc_fields

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.ajsystem.defs.data import (
    resolve_entity_fields, page_list_cfg as _lista_config, module_page,
)
from app.ajsystem.defs.form import Form
from app.ajsystem.core.adapter import db
from app.ajsystem.core.do_list import do_list
from app.ajsystem.core.do_form import do_form
from app.ajsystem.core.form import _resolve_delete, _when_allows


def _normalizar_slug(label: str) -> str:
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _blueprint_no_modulo(mod):
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
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


def _entidade_principal(mod):
    form = _form_config(mod)
    if form:
        fields = form.get('fields')
        if isinstance(fields, str):
            return fields
    lista = _lista_config(mod)
    if isinstance(lista, dict):
        fields = lista.get('fields')
        if isinstance(fields, str):
            return fields
        columns = fields or []
        if columns:
            primeira = columns[0]
            if isinstance(primeira, str):
                return primeira.split('.', 1)[0]
    entidades = getattr(mod, 'Schema', {}) or {}
    if entidades:
        return next(iter(entidades))
    return None


def _get_model(mod):
    entidade = _entidade_principal(mod)
    if entidade:
        cand = getattr(mod, entidade, None)
        if isinstance(cand, type) and getattr(cand, '__table__', None) is not None:
            return cand
    form = _form_config(mod)
    if isinstance(form.get('model'), type):
        return form['model']
    return None


def _toggle_field(form_cfg):
    for b in form_cfg.get('buttons') or []:
        if b == 'on_off':
            return 'ativo'
        if isinstance(b, dict) and len(b) == 1 and 'on_off' in b:
            return (b['on_off'] or {}).get('field') or 'ativo'
        if isinstance(b, dict) and b.get('on_off') is True and b.get('field'):
            return b['field']
    return None


def _build_form(mod, entidade, model, slug=None):
    cfg = dict(_form_config(mod))
    if 'pre_get' in cfg:
        cfg.pop('pre_get')
    cfg.setdefault('fields', entidade)
    allowed = {f.name for f in dc_fields(Form)}
    form = Form(**{k: v for k, v in cfg.items() if k in allowed})
    schema = getattr(mod, 'Schema', None) or {}
    schema_merged = resolve_entity_fields(schema, model, entidade)
    form.resolve(entidade, model, schema_merged, blueprint=slug)
    if slug:
        form._redirect = f"{slug}.list"
    if hasattr(mod, '_label') and not form._label:
        form._label = getattr(mod, '_label')
    return form


def _generated_crud(mod, slug):
    page = getattr(mod, 'Page', None)
    if isinstance(page, dict):
        if page.get('type', 'crud') != 'crud':
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
        form = _build_form(mod, entidade, model, slug=slug)
        extra = None
        pre_get = _form_config(mod).get('pre_get')
        if callable(pre_get):
            extra = pre_get(mod, id)
        return do_form(form, id, extra_ctx=extra)
    routes.append(('/novo', 'form', _form))
    routes.append(('/<int:id>/editar', 'form', _form))

    del_cfg = _resolve_delete(form_cfg.get('delete'), label=entidade)
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
        flash_toggle = 'Atualizado!'

        def _toggle(id):
            instance = model.query.get_or_404(id)
            setattr(instance, campo, not getattr(instance, campo))
            db.session.commit()
            flash(flash_toggle, 'success')
            return redirect(url_for(f'{slug}.form', id=id))
        routes.append(('/<int:id>/toggle', 'toggle', _toggle))

    return routes


def montar_blueprint(mod, slug=None, url_prefix=None, login=True, label=None):
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

    generated = _generated_crud(mod, slug)
    for rule, endpoint, func in generated:
        if rule == '/novo':
            methods = ('GET', 'POST')
            bp.add_url_rule(rule, endpoint, func, methods=methods, defaults={'id': None})
        elif endpoint == 'form':
            bp.add_url_rule(rule, endpoint, func, methods=('GET', 'POST'))
        elif endpoint == 'delete':
            bp.add_url_rule(rule, endpoint, func, methods=('POST',))
        else:
            bp.add_url_rule(rule, endpoint, func, methods=('GET',))

    setattr(mod, 'bp', bp)
    return bp


def _iterar_itens_menus(modulo_menu):
    for label, item in modulo_menu.items():
        if item.submenus:
            yield from _iterar_itens_menus(item.submenus)
        yield label, item


def _blueprint_construcao(slug, label=None, login=True, url_prefix=None):
    bp = Blueprint(slug, f'{__name__}.{slug}', url_prefix=url_prefix or f'/{slug}')
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
    registrados = []
    vistos = set()
    para_site = modulo_ini.endswith('.site')
    for label, item in _iterar_itens_menus(modulo_menu):
        if item.url:
            continue
        slug = _normalizar_slug(item.page or label)
        if slug in vistos:
            continue
        vistos.add(slug)
        bp_slug = f'site_{slug}' if para_site else slug
        try:
            mod = importlib.import_module(f'{modulo_ini}.{slug}')
        except ImportError:
            bp = _blueprint_construcao(bp_slug, label=label, login=login,
                                       url_prefix=f'/{bp_slug}')
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
            bp = montar_blueprint(mod, slug=bp_slug, url_prefix=prefix, label=label, login=login)
        else:
            bp = montar_blueprint(mod, bp_slug, label=label, login=login)
        if bp is None:
            continue
        app.register_blueprint(bp)
        registrados.append(bp.name)

    if para_site:
        _registrar_rotas_automaticas(app)
    return registrados


def _registrar_rotas_automaticas(app):
    """Rotas automáticas públicas: `/` → redirect (logado → /sistema, senão /sobre)
    e `/sistema` → páginas/construcao (login_required). Somente se ausentes."""
    from flask import redirect as flask_redirect, render_template
    from flask_login import login_required, current_user

    has_root = any(r.rule == '/' for r in app.url_map.iter_rules())
    if not has_root:
        @app.route('/')
        def _site_root():
            if current_user.is_authenticated:
                return flask_redirect('/sistema')
            return flask_redirect('/sobre')

    has_sistema = any(r.rule == '/sistema' for r in app.url_map.iter_rules())
    if not has_sistema:
        @app.route('/sistema')
        @login_required
        def _site_sistema():
            return render_template('pages/construcao.html')
