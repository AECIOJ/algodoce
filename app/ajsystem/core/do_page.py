"""Orquestrador de páginas únicas (`Page` com `type` não-`crud`).

A spec `Page` descreve a página via `type`:

- `'custom'` (default): renderiza `template` (`html` ou `markdown`).
- `'cart'`: carrinho declarativo (sessões table/form + envio).
- `'showcase'`: vitrine declarativa (catálogo + carrinho).
- `'contacts'`: lista de contatos (props = dict de contatos).
- `'redirect'`: redirecionamento (props.target / props.auth_target).

Em `type: 'custom'`, `template` é obrigatório:
- `{'type': 'html', 'file': '...'}` → renderiza template. Contexto de
  `context()` no módulo ou de `events.on_show` (pre-render).
- `{'type': 'markdown', 'file': '...'}` → renderiza markdown na template
  padrão do motor `pages/markdown.html`.

`events.on_show` (callable, opcional): chamado antes de renderizar;
se retornar `dict`, mergeia no contexto da template.

`events.on_send` (callable, opcional): disparado após envio do cart.
"""
from flask import abort, redirect as flask_redirect, render_template

from app.ajsystem.core.adapter import get_markdown_loader
from app.ajsystem.core.cart import cart_context
from app.ajsystem.core.showcase import showcase_context

_ROUTES_PREFIX = 'app.routes.'


def _nome_rotas(mod):
    nome = getattr(mod, '__name__', '')
    if nome.startswith(_ROUTES_PREFIX):
        return nome[len(_ROUTES_PREFIX):]
    return nome


def _pasta_do_modulo(mod):
    """Pasta de templates do módulo: `app.routes.<pacote>.<modulo>` → `<pacote>`."""
    return '/'.join(_nome_rotas(mod).split('.')[:-1])


def _slug_do_modulo(mod):
    return _nome_rotas(mod).rsplit('.', 1)[-1]


def _rota_do_modulo(mod, page):
    """Subpasta da página: `route` declarado no Page, senão o slug do módulo."""
    if isinstance(page, dict) and page.get('route') is not None:
        return str(page['route'])
    return _slug_do_modulo(mod)


def _arquivo_markdown(mod, nome):
    """Resolve o `file` de markdown para caminho relativo na pasta de templates.

    `'sobre'` vira `site/sobre.md` (pacote do módulo + extensão `.md`); nome com
    `/` ou terminando em `.md` é mantido como caminho explícito.
    """
    if '/' in nome or nome.endswith('.md'):
        return nome
    pasta = _pasta_do_modulo(mod)
    return f'{pasta}/{nome}.md' if pasta else f'{nome}.md'


def _arquivo_html(mod, page, nome):
    """Resolve o `file` de html para caminho relativo na pasta de templates.

    Omitido → `'index'`; `'navegador'` vira `site/vitrine/navegador.html`
    (pacote do módulo + `route`/slug + extensão `.html`); nome com `/` ou
    terminando em `.html` é mantido como caminho explícito.
    """
    nome = nome or 'index'
    if '/' in nome or nome.endswith('.html'):
        return nome
    pasta = _pasta_do_modulo(mod)
    rota = _rota_do_modulo(mod, page)
    return f'{pasta}/{rota}/{nome}.html' if pasta else f'{rota}/{nome}.html'


def _call_on_show(spec, ctx):
    """Chama events.on_show (pre-render) e mergeia resultado no contexto."""
    events = spec.get('events') or {}
    on_show = events.get('on_show')
    if callable(on_show):
        extra = on_show()
        if isinstance(extra, dict):
            ctx.update(extra)


def do_page(mod):
    spec = getattr(mod, 'Page', None)
    if not isinstance(spec, dict):
        abort(404)

    page_type = spec.get('type', 'custom')
    props = spec.get('props') or {}
    template = spec.get('template') or {}

    # Redirect
    if page_type == 'redirect':
        target = props.get('target', '/')
        auth_target = props.get('auth_target')
        if auth_target:
            from flask_login import current_user
            if current_user.is_authenticated:
                return flask_redirect(auth_target)
        return flask_redirect(target)

    # Carrinho declarativo (Page type='cart')
    if page_type == 'cart':
        ctx = cart_context(mod)
        if ctx is None:
            abort(404)
        _call_on_show(spec, ctx)
        return render_template(
            'pages/cart.html', page=spec, module_name=mod.__name__, **ctx,
        )

    # Vitrine declarativa (Page type='showcase')
    if page_type == 'showcase':
        ctx = showcase_context(mod)
        if ctx is None:
            abort(404)
        _call_on_show(spec, ctx)
        return render_template(
            'pages/showcase.html', page=spec, module_name=mod.__name__, **ctx,
        )

    # Contacts (Page type='contacts')
    if page_type == 'contacts':
        ttype = template.get('type', 'html')
        tfile = _arquivo_html(mod, spec, template.get('file'))
        ctx = {'contacts': props}
        _call_on_show(spec, ctx)
        return render_template(tfile, page=spec, module_name=mod.__name__, **ctx)

    # Custom (default)
    ttype = template.get('type', 'html')

    if ttype == 'markdown':
        loader = get_markdown_loader()
        nome = template.get('file')
        if loader is None or not nome:
            abort(404)
        content = loader(_arquivo_markdown(mod, nome))
        if content is None:
            abort(404)
        ctx = {}
        _call_on_show(spec, ctx)
        return render_template(
            'pages/markdown.html', content=content, page=spec, module_name=mod.__name__, **ctx,
        )

    if ttype == 'html':
        tfile = _arquivo_html(mod, spec, template.get('file'))
        ctx = {}
        context_cfg = template.get('context')
        if callable(context_cfg):
            fn = context_cfg
        else:
            fn = getattr(mod, context_cfg or 'context', None)
        if callable(fn):
            extra = fn()
            if isinstance(extra, dict):
                ctx.update(extra)
        _call_on_show(spec, ctx)
        return render_template(tfile, page=spec, module_name=mod.__name__, **ctx)

    abort(404)
