"""Páginas de conteúdo estático ("conteúdo como código").

Cada página vive em `app/templates/<pacote>/<slug>.md` (mesmo caminho relativo
do módulo de rotas; ex.: `app.routes.site.sobre` → `site/sobre.md`), com as
mídias em `app/static/...` referenciadas por URL. O markdown é convertido para
HTML uma única vez (cache por mtime) e sanitizado (nh3) antes de chegar ao
template.
"""
import os
import re

import markdown
import nh3
from flask import current_app

_SLUG_OK = re.compile(r'^[a-z0-9_./-]+$')

_TAGS = {
    'p', 'br', 'hr', 'strong', 'em', 'b', 'i', 'u', 'del', 'ins', 'sup', 'sub',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
    'blockquote', 'code', 'pre', 'a', 'img', 'table', 'thead', 'tbody',
    'tfoot', 'tr', 'th', 'td', 'caption', 'figure', 'figcaption', 'span', 'div',
}

_ATTRS = {
    'a': {'href', 'title'},
    'img': {'src', 'alt', 'title'},
    'code': {'class'},
    'span': {'class'},
    'div': {'class'},
    'td': {'colspan', 'rowspan'},
    'th': {'colspan', 'rowspan'},
}

_cache = {}


def _pasta():
    return os.path.join(current_app.root_path, 'templates')


def render_pagina(nome):
    """Renderiza `<caminho>.md` (relativo à pasta de templates) para HTML
    sanitizado, ou None se ausente. Rejeita caminhos absolutos e `..`."""
    if not isinstance(nome, str) or not _SLUG_OK.match(nome):
        return None
    if nome.startswith('/') or '..' in nome:
        return None
    path = os.path.join(_pasta(), nome)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    entrada = _cache.get(nome)
    if entrada is not None and entrada[0] == mtime:
        return entrada[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            texto = f.read()
    except OSError:
        return None
    html = markdown.markdown(texto, extensions=['extra'])
    html = nh3.clean(html, tags=_TAGS, attributes=_ATTRS, link_rel='noopener noreferrer')
    _cache[nome] = (mtime, html)
    return html
