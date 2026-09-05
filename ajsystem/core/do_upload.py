"""Uploads de imagem (serving + temporários + commit no save).

Substitui `app/routes/uploads.py`. Política resolvida em:
`Page.upload` → `App.upload` → defaults (iguais ao comportamento anterior).
"""
import os

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import login_required

bp = Blueprint("uploads", __name__)

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def resolve_policy(page_upload=None):
    """Política efetiva: `DEFAULT_UPLOAD` ← `App.upload` ← `Page.upload`."""
    from ajsystem.defs.config import DEFAULT_UPLOAD
    policy = dict(DEFAULT_UPLOAD)
    from ajsystem.core.adapter import APP
    policy.update(getattr(APP, 'upload', None) or {})
    policy.update(page_upload or {})
    return policy


def _upload_root():
    return os.path.join(current_app.root_path, '..', 'dados', 'uploads')


def _delete_uploaded(filename):
    if not filename:
        return
    root = _upload_root()
    rel = os.path.normpath(filename)
    if rel.startswith('..') or os.path.isabs(rel):
        return
    path = os.path.join(root, rel)
    try:
        inside = os.path.commonpath([os.path.abspath(root), os.path.abspath(path)]) == os.path.abspath(root)
    except ValueError:
        inside = False
    if inside and os.path.exists(path) and os.path.isfile(path):
        os.remove(path)


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(_upload_root(), filename)


@bp.route('/image-temp-upload', methods=['POST'])
@login_required
def image_temp_upload():
    import base64
    import re as _re
    import uuid
    data = request.get_json(silent=True)
    if not data or 'imagem' not in data:
        return jsonify(error='Nenhuma imagem'), 400
    match = _re.match(r'data:image/(\w+);base64,(.+)', data['imagem'])
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


@bp.route('/image-temp-remove', methods=['POST'])
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


def process_image_fields(form, instance):
    """Move temp→final no save (chamado pelo `do_form`). Retorna alterados."""
    from flask import flash
    policy = resolve_policy(getattr(form, 'upload', None))
    allowed = {str(e).lower().lstrip('.') for e in (policy.get('allowed') or [])}
    max_size = policy.get('max_size')
    try:
        max_size = int(max_size) if max_size is not None else None
    except (TypeError, ValueError):
        max_size = None
    rel = (policy.get('path') or '').strip('/')
    changed = set()
    for f in form._resolved_fields:
        if f.input != 'image' or f.pos_form != 1:
            continue
        name = f.name
        old = getattr(instance, name, None)
        temp = request.form.get(f'temp_imagem_{name}', '').strip()
        remover = request.form.get(f'remover_imagem_{name}', '').strip() in ('1', 'on')
        if temp.startswith('temp_'):
            root = _upload_root()
            temp_path = os.path.join(root, os.path.basename(temp))
            if os.path.exists(temp_path):
                if max_size is not None:
                    try:
                        size = os.path.getsize(temp_path)
                    except OSError:
                        size = None
                    if size is not None and size > max_size:
                        flash(f'{f.label or name} excede o tamanho máximo.', 'warning')
                        continue
                ext = temp.rsplit('.', 1)[-1].lower()
                if allowed and ext not in allowed:
                    flash(f'{f.label or name} em formato não permitido.', 'warning')
                    continue
                final_dir = os.path.join(root, rel) if rel else root
                os.makedirs(final_dir, exist_ok=True)
                final = f'{instance.__class__.__tablename__}_{instance.id}_{name}.{ext}'
                final_name = f'{rel}/{final}' if rel else final
                if old:
                    _delete_uploaded(old)
                os.rename(temp_path, os.path.join(final_dir, final))
                setattr(instance, name, final_name)
        elif remover and old:
            _delete_uploaded(old)
            setattr(instance, name, None)
        if getattr(instance, name, None) != old:
            changed.add(name)
    return changed
