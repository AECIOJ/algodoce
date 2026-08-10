import importlib
import unicodedata
from flask import Blueprint, url_for, request, current_app
from flask_login import current_user

from app.ajsystem.core.app_config import APP


def _normalizar_slug(label: str) -> str:
    """Remove acentos, ç e minúsculas → slug do módulo de página."""
    s = unicodedata.normalize('NFKD', label or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def _modulo_pagina(slug: str):
    """Retorna o módulo app.routes.sys.<slug> ou None se não existir."""
    try:
        return importlib.import_module(f'app.routes.sys.{slug}')
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
        return APP['system']
    return APP['site']


def url_do_item(item, label=None):
    """Resolve a URL de um item de menu.

    - item com 'endpoint' explícito → usa (página custom/editada).
    - caso contrário → normaliza o rótulo em slug → módulo app.routes.sys.<slug>
      → URL do blueprint.list. Módulo inexistente → página 'Em construção'.
    """
    if 'endpoint' in item:
        return url_for(item['endpoint'])
    if item.get('url'):
        return item['url']
    slug = _normalizar_slug(label or '')
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
    result = {}
    for label, item in mod['menus'].items():
        sub = item.get('submenus')
        if sub:
            result[label.lower()] = {
                'title': label,
                'items': [
                    {'label': sl, 'url': url_do_item(si, sl), 'icon': si.get('icon', '')}
                    for sl, si in sub.items()
                ],
            }
    return result


def pagina_home(mod=None):
    """URL inicial do módulo: 'home' declarado → padrão interno (1º menu) → '/'.

    'home' pode apontar para qualquer endpoint válido, mesmo fora de 'menus'.
    """
    if mod is None:
        mod = modulo_atual()
    home = mod.get('home')
    if home:
        try:
            return url_for(home)
        except Exception:
            return '/'
    for label, item in mod.get('menus', {}).items():
        sub = item.get('submenus')
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
