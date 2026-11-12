"""Menu — resolução de URLs da árvore de menus registrada no config.

Reescrito do zero observando `core/old/menu.py`. Consome a estrutura
`App`/`Module`/`MenuItem` de `defs.config`. Módulos ausentes apontam para a
página `ajsystem.construcao`.
"""
import importlib

from flask import url_for, request, current_app
from flask_login import current_user

from ajsystem.core.adapter import APP
from ajsystem.core.utils import module_blueprint, normalizar_slug


def _module_page(slug: str, modulo_ini=None):
    from ajsystem.core.adapter import ROUTES_BASE
    try:
        return importlib.import_module(f'{modulo_ini or ROUTES_BASE + ".sys"}.{slug}')
    except ImportError:
        return None


# Pacote de rotas de cada tipo de módulo: o menu resolve o módulo do item no
# subpacote do PRÓPRIO módulo (`public` → `site`, `system` → `sys`, `admin` →
# `admin`). Sem isso, um item do site com slug que também existe no sys
# (ex.: 'Produtos') cairia no módulo errado, e slugs só existentes no site
# cairiam em `construcao`.
_PACOTE_POR_TIPO = {'system': 'sys', 'public': 'site', 'admin': 'admin'}


def _pacote_do_modulo(mod):
    tipo = getattr(mod, 'type', '') if mod else ''
    pacote = _PACOTE_POR_TIPO.get(tipo)
    if not pacote:
        from ajsystem.core.adapter import ROUTES_BASE
        return ROUTES_BASE + '.sys'
    from ajsystem.core.adapter import ROUTES_BASE
    return f'{ROUTES_BASE}.{pacote}'


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


def url_do_item(item, label=None, mod=None):
    """Resolve a URL de um item de menu (endpoint, caminho literal ou módulo).

    Item sem url → módulo `<slug>.py` no subpacote do módulo dono do menu
    (`mod`; ausente → módulo atual) → URL do blueprint `.list`. Módulo
    ausente (página não migrada) → `ajsystem.construcao`.
    """
    if item.url:
        if item.url.startswith('/') or '://' in item.url:
            return item.url
        try:
            return url_for(item.url)
        except Exception:
            slug = normalizar_slug(item.page or label or '')
            return url_for('ajsystem.construcao', pagina=slug)
    if mod is None:
        mod = modulo_atual()
    slug = normalizar_slug(item.page or label or '')
    m = _module_page(slug, _pacote_do_modulo(mod))
    if m is None:
        return url_for('ajsystem.construcao', pagina=slug)
    bp = module_blueprint(m)
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
                    {'label': sl, 'url': url_do_item(si, sl, mod), 'icon': si.icon or ''}
                    for sl, si in sub.items()
                ],
            }
    return result


def _find_by_slug(items, slug):
    for label, item in items.items():
        if normalizar_slug(item.page or label) == slug:
            return label, item
    return None


def _resolver_default(mod, value):
    if not value:
        return None
    if value.startswith('/'):
        return value
    if '.' in value:
        try:
            return url_for(value)
        except Exception:
            return None
    segs = [s for s in value.split('/') if s]
    items = mod.menus
    for i, seg in enumerate(segs):
        found = _find_by_slug(items, seg)
        if found is None:
            return None
        label, item = found
        if i == len(segs) - 1:
            break
        if not item.submenus:
            return None
        items = item.submenus
    try:
        url = url_do_item(item, label, mod)
    except Exception:
        url = None
    if url and not url.startswith('/ajsystem/construcao'):
        return url
    if item.submenus:
        for sl, si in item.submenus.items():
            try:
                u = url_do_item(si, sl, mod)
            except Exception:
                continue
            if u and not u.startswith('/ajsystem/construcao'):
                return u
    return None


def home_page(mod=None):
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
                    url = url_do_item(si, sl, mod)
                except Exception:
                    continue
                if url and not url.startswith('/ajsystem/construcao'):
                    return url
        else:
            try:
                url = url_do_item(item, label, mod)
            except Exception:
                continue
            if url and not url.startswith('/ajsystem/construcao'):
                return url
    return '/'


def caminho_atual(path=None):
    """Caminho completo do menu ativo (lista de rótulos, do nível 1 ao folha).

    Resolve `request.path` (ou `path` dado) contra a árvore de menus do módulo
    atual com a MESMA regra de `item_ativo` (igualdade ou prefixo de rota —
    páginas filhas de um módulo, ex.: form sob o list, herdam o trail do
    folha). Vence o trail mais profundo que casa. Ex.: `Financeiro ➔ Contas
    a Receber`. Sem casamento (rota fora do menu, ex.: painel admin) → `[]`.
    """
    if path is None:
        path = request.path
    p = (path or '').rstrip('/') or '/'
    mod = modulo_atual()
    if mod is None:
        return []
    best = []

    def walk(items, acc):
        nonlocal best
        for label, item in items.items():
            trail = acc + [label]
            try:
                href = url_do_item(item, label, mod).rstrip('/')
            except Exception:
                href = None
            if href and (p == href or (href != '/' and p.startswith(href + '/'))
                         ) and len(trail) > len(best):
                best = trail
            if item.submenus:
                walk(item.submenus, trail)

    walk(mod.menus, [])
    return best
