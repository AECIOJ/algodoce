"""Acoplamento do framework com a aplicação host.

Ponto único de import das dependências específicas do projeto (SQLAlchemy db,
login manager, modelos User/Setting, config APP) mais hooks opcionais de
markdown/túnel. Para portar o framework a outro host, ajustar este arquivo.
"""
import os

from flask import current_app

from ajsystem.core.extensions import db, login_manager
from app.models.user import User
from app.models.setting import Setting
from app import config as _config_mod
from app.config import APP as _APP, Temas as _TEMAS
from ajsystem.defs.config import build_app, build_temas

_versao_path = os.path.join(os.path.dirname(os.path.abspath(_config_mod.__file__)), 'versao.py')
APP = build_app(_APP, versao_path=_versao_path)
TEMAS = build_temas(_TEMAS)

# Pacote base das rotas do host (módulos `sys`/`site` pendurados dele).
# Para portar o framework a outro layout, ajustar aqui (os chamadores que
# aceitam `modulo_ini` já permitem override por chamada).
ROUTES_BASE = 'app.routes'


def get_uploads_endpoint(app=None):
    """Endpoint usado pelas templates oara servir uploads de imagem."""
    return (app or current_app).config.get('AJ_UPLOADS_ENDPOINT', 'uploads.uploaded_file')


# ─── Markdown de conteúdo (páginas `type='markdown'`) ────────────────────────
_markdown_loader = None


def set_markdown_loader(fn):
    global _markdown_loader
    _markdown_loader = fn


def get_markdown_loader():
    return _markdown_loader


# ─── URL pública (QR de acesso) ─────────────────────────────────────────────
_tunnel_url_provider = None


def set_tunnel_url_provider(fn):
    global _tunnel_url_provider
    _tunnel_url_provider = fn


def get_tunnel_url():
    return _tunnel_url_provider() if _tunnel_url_provider else None
