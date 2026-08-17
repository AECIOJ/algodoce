import importlib
import unicodedata
from flask import Blueprint, url_for, request, current_app
from flask_login import current_user

from app.ajsystem.core.adapter import APP


def _normalizar_slug(label: str) -> str:
    """Remove acentos, ç e minúsculas → slug do módulo de página."""
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _modulo_ini_do_contexto():
    """Pacote de rotas do módulo atual: site (`public`) vs sistema (`sys`)."""
    mod = modulo_atual()
    return 'app.routes.site' if mod and mod.type == 'public' else 'app.routes.sys'


def _modulo_pagina(slug: str, modulo_ini=None):
    """Retorna o módulo `<pacote>.<slug>` ou None se não existir.

    `modulo_ini` default é derivado do módulo ativo (público → `app.routes.site`).
    """
    if not modulo_ini:
        modulo_ini = _modulo_ini_do_contexto()
    try:
        return importlib.import_module(f'{modulo_ini}.{slug}')
    except ImportError:
        return None


def _blueprint_do_modulo(mod):
    for name in dir(mod):
        obj = getattr(mod, name, None)
        if isinstance(obj, Blueprint):
            return obj
    return None


def _endpoint_lista(bp):
    """Endpoint de listagem do blueprint: 'list' ou o 1º endpoint registrado."""
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
    """Resolve a URL de um item de menu.

    - item com `url` → rota registrada (nome de endpoint → url_for) ou caminho
      literal ('/pagina', 'https://...').
    - caso contrário → arquivo do módulo (`page` ou rótulo normalizado) →
      módulo `<pacote do módulo ativo>.<slug>` → URL do blueprint.list.
      Módulo inexistente → página 'Em construção'.
    """
    if item.url:
        if item.url.startswith('/') or '://' in item.url:
            return item.url
        return url_for(item.url)
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
    """Encontra (label, item) cujo slug (page ou rótulo) casa com o segmento."""
    for label, item in itens.items():
        if _normalizar_slug(item.page or label) == slug:
            return label, item
    return None


def _resolver_default(mod, valor):
    """Resolve `default_path` em URL: literal → endpoint nomeado → caminho de menu.

    - literal: '/pagina' → devolve como está;
    - endpoint nomeado (contém '.', ex.: 'seguranca.painel') → url_for;
    - caminho de menu 'secao/item' → percorre a árvore; seção (com submenus)
      como alvo → 1º submenu navegável.
    Retorna None se não resolver.
    """
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
    """URL inicial do módulo: 'default_path' declarado → padrão interno (1º menu) → '/'.

    'default_path' aceita endpoint nomeado ('seguranca.painel'), caminho literal
    ('/manual') ou caminho de menu ('cadastro/categorias', 'cadastro').
    """
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
