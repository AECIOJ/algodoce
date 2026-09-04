import base64
import os
import re
import uuid
from flask import Blueprint, current_app, jsonify, request, render_template, url_for
from markupsafe import Markup
from flask_login import login_required

ajsystem = Blueprint('ajsystem', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/ajsystem',
    url_prefix='/ajsystem')


def _upload_root():
    return os.path.join(current_app.root_path, '..', 'dados', 'uploads')


ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


@ajsystem.route('/image-temp-upload', methods=['POST'])
@login_required
def image_temp_upload():
    data = request.get_json(silent=True)
    if not data or 'imagem' not in data:
        return jsonify(error='Nenhuma imagem'), 400
    match = re.match(r'data:image/(\w+);base64,(.+)', data['imagem'])
    if not match:
        return jsonify(error='Formato inválido'), 400
    ext = match.group(1).lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return jsonify(error='Formato não permitido'), 400
    raw = base64.b64decode(match.group(2))
    root = _upload_root()
    os.makedirs(root, exist_ok=True)
    nome = f'temp_{uuid.uuid4().hex}.{ext}'
    with open(os.path.join(root, nome), 'wb') as f:
        f.write(raw)
    return jsonify(success=True, filename=nome)


@ajsystem.route('/image-temp-remove', methods=['POST'])
@login_required
def image_temp_remove():
    data = request.get_json(silent=True)
    filename = (data or {}).get('filename', '')
    if not filename or not filename.startswith('temp_'):
        return jsonify(error='Arquivo inválido'), 400
    path = os.path.join(_upload_root(), os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
    return jsonify(success=True)


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
        mod = importlib.import_module(f'app.routes.sys.{page}')
    except ImportError:
        return jsonify(error='página desconhecida'), 404
    spec = getattr(mod, name, None)
    if not isinstance(spec, dict):
        return jsonify(error='busca desconhecida'), 404
    from app.ajsystem.core import search as _search
    params = {k: v for k, v in request.args.items() if k not in ('page', 'query')}
    return jsonify(_search.run_search(spec, params))


from app.ajsystem.init import init_app  # noqa: E402  (wiring do framework)
