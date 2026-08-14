"""Ponto único de acoplamento do framework com a aplicação host.

O framework (app.ajsystem) só importa deste módulo as dependências
específicas do projeto: SQLAlchemy db, login manager, modelos User/Setting,
config APP e o endpoint de uploads. Para portar o framework para outro
projeto, basta substituir/implementar as funções deste arquivo.
"""
import os

from flask import current_app

from app.ajsystem.core.extensions import db, login_manager
from app.models.user import User
from app.models.setting import Setting
from app import config as _config_mod
from app.config import APP as _APP, Temas as _TEMAS
from app.ajsystem.defs.config import build_app, build_temas

_versao_path = os.path.join(os.path.dirname(os.path.abspath(_config_mod.__file__)), 'versao.py')
APP = build_app(_APP, versao_path=_versao_path)
TEMAS = build_temas(_TEMAS)


def get_uploads_endpoint(app=None):
    """Endpoint usado pelas templates para servir uploads de imagem.

    Pode ser sobrescrito via config `AJ_UPLOADS_ENDPOINT`.
    """
    return (app or current_app).config.get('AJ_UPLOADS_ENDPOINT', 'uploads.uploaded_file')


# ─── URL pública (QR de acesso) ─────────────────────────────────────────────

_tunnel_url_provider = None


def set_tunnel_url_provider(fn):
    """Registra a implementação de URL pública do host (ex.: túnel)."""
    global _tunnel_url_provider
    _tunnel_url_provider = fn


def get_tunnel_url():
    """URL pública do app p/ QR de acesso; padrão: `None` (fallback no endpoint)."""
    return _tunnel_url_provider() if _tunnel_url_provider else None
