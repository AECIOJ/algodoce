"""Menu — resolução de URLs da árvore de menus registrada no config.

Reescrito do zero observando `core/old/menu.py`. Consome a estrutura
`App`/`Module`/`MenuItem` de `defs.config`. Módulos ausentes apontam para a
página `ajsystem.construcao`.
"""
import importlib
import unicodedata

from flask import Blueprint, url_for, request, current_app
from flask_login import current_user

from ajsystem.core.adapter import APP


def _normalizar_slug(label: str) -> str:
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _modulo_pagina(slug: str, modulo_ini=None):
    from ajsystem.core.adapter import ROUTES_BASE
    try:
        return importlib.import_module(f'{modulo_ini or ROUTES_BASE + ".sys"}.{slug}')
    except ImportError:
        return None


def _blueprint_do_modulo(mod):
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
    return None


def _endpoint_lista(bp):
    vf = current_app.view_functions
    prefixo = f'{bp.name}.'
    nomes = [k[len(prefixo):] for k in vf if k.startswith(prefixo)]
    if 'list' in nomes:
        return f'{bp.name}.list'
    if nomes:
        return f'{bp.name}.{nomes[0]}'
    return None


def modulo_atual():
    if current_user.is_authenticated:
        return APP.module('system')
    return APP.module('public')


def url_do_item(item, label=None):
    """Resolve a URL de um item de menu (endpoint, caminho literal ou módulo).

    Item sem url → módulo `<slug>.py` → URL do blueprint `.list`. Módulo
    ausente (página não migrada) → `ajsystem.construcao`.
    """
    if item.url:
        if item.url.startswith('/') or '://' in item.url:
            return item.url
        try:
            return url_for(item.url)
        except Exception:
            slug = _normalizar_slug(item.page or label or '')
            return url_for('ajsystem.construcao', pagina=slug)
    slug = _normalizar_slug(item.page or label or '')
    mod = _modulo_pagina(slug)
    if mod is None:
        return url_for('ajsystem.construcao', pagina=slug)
    bp = _blueprint_do_modulo(mod)
    if bp is None:
        return url_for('ajsystem.construcao', pagina=slug)
    endpoint = _endpoint_lista(bp)
    if endpoint is None:
        return url_for('ajsystem.construcao', pagina=slug)
    return url_for(endpoint)


def item_ativo(item, path):
    href = url_do_item(item)
    return path.rstrip('/') == href.rstrip('/') or path.startswith(href.rstrip('/') + '/')


def menus_para_json():
    mod = modulo_atual()
    if mod is None:
        return {}
    result = {}
    for label, item in mod.menus.items():
        sub = item.submenus
        if sub:
            result[label.lower()] = {
                'title': label,
                'items': [
                    {'label': sl, 'url': url_do_item(si, sl), 'icon': si.icon or ''}
                    for sl, si in sub.items()
                ],
            }
    return result


def _achar_por_slug(itens, slug):
    for label, item in itens.items():
        if _normalizar_slug(item.page or label) == slug:
            return label, item
    return None


def _resolver_default(mod, valor):
    if not valor:
        return None
    if valor.startswith('/'):
        return valor
    if '.' in valor:
        try:
            return url_for(valor)
        except Exception:
            return None
    segs = [s for s in valor.split('/') if s]
    itens = mod.menus
    for i, seg in enumerate(segs):
        achado = _achar_por_slug(itens, seg)
        if achado is None:
            return None
        label, item = achado
        if i == len(segs) - 1:
            break
        if not item.submenus:
            return None
        itens = item.submenus
    try:
        url = url_do_item(item, label)
    except Exception:
        url = None
    if url and not url.startswith('/ajsystem/construcao'):
        return url
    if item.submenus:
        for sl, si in item.submenus.items():
            try:
                u = url_do_item(si, sl)
            except Exception:
                continue
            if u and not u.startswith('/ajsystem/construcao'):
                return u
    return None


def pagina_home(mod=None):
    if mod is None:
        mod = modulo_atual()
    if mod is None:
        return '/'
    url = _resolver_default(mod, mod.default_path)
    if url:
        return url
    for label, item in mod.menus.items():
        sub = item.submenus
        if sub:
            for sl, si in sub.items():
                try:
                    url = url_do_item(si, sl)
                except Exception:
                    continue
                if url and not url.startswith('/ajsystem/construcao'):
                    return url
        else:
            try:
                url = url_do_item(item, label)
            except Exception:
                continue
            if url and not url.startswith('/ajsystem/construcao'):
                return url
    return '/'
