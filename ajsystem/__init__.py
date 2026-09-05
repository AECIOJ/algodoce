import re
from flask import Blueprint, jsonify, request, render_template, url_for
from markupsafe import Markup
from flask_login import login_required

ajsystem = Blueprint('ajsystem', __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/ajsystem')


@ajsystem.app_template_filter('heroicon')
def heroicon_filter(name, class_='w-5 h-5'):
    return Markup(
        f'<svg class="{class_}" aria-hidden="true">'
        f'<use href="#i-{name}"/></svg>'
    )


@ajsystem.route('/construcao')
@login_required
def construcao():
    pagina = request.args.get('pagina', '')
    return render_template('pages/construcao.html', pagina=pagina)


@ajsystem.route('/api/tunnel-url')
@login_required
def tunnel_url():
    """URL pública atual do túnel (para o QR code)."""
    from ajsystem.core.adapter import get_tunnel_url
    return jsonify(url=get_tunnel_url() or '')


@ajsystem.route('/lookup-search')
@login_required
def lookup_search():
    """JSON de busca declarada p/ modal de lookup (`Lookup.query`).

    `?page=<slug>&query=<NOME>[&<param>=<valor>...]` — importa
    `app.routes.sys.<slug>`, lê a declaração e executa via `core.search`.
    Slug/nome restritos a `[A-Za-z0-9_]` (sem import arbitrário).
    """
    import importlib
    page = request.args.get('page', '') or ''
    name = request.args.get('query', '') or ''
    if not re.fullmatch(r'[A-Za-z0-9_]+', page) or not re.fullmatch(r'[A-Za-z0-9_]+', name):
        return jsonify(error='parâmetros inválidos'), 400
    try:
        from ajsystem.core.adapter import ROUTES_BASE
        mod = importlib.import_module(f'{ROUTES_BASE}.sys.{page}')
    except ImportError:
        return jsonify(error='página desconhecida'), 404
    spec = getattr(mod, name, None)
    if not isinstance(spec, dict):
        return jsonify(error='busca desconhecida'), 404
    from ajsystem.core import search as _search
    params = {k: v for k, v in request.args.items() if k not in ('page', 'query')}
    return jsonify(_search.run_search(spec, params))


from ajsystem.init import init_app  # noqa: E402  (wiring do framework)
