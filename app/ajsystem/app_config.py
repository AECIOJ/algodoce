"""Ponto único de acoplamento do framework com a aplicação host.

O framework (app.ajsystem) só importa deste módulo as dependências
específicas do projeto: SQLAlchemy db, login manager, modelos User/Setting,
config APP/SYS e o endpoint de uploads. Para portar o framework para outro
projeto, basta substituir/implementar as funções deste arquivo.
"""
from flask import current_app

from app.extensions import db, login_manager
from app.models.user import User
from app.models.setting import Setting
from app.routes.app_defs import APP, SYS


def get_uploads_endpoint(app=None):
    """Endpoint usado pelas templates para servir uploads de imagem.

    Pode ser sobrescrito via config `AJ_UPLOADS_ENDPOINT`.
    """
    return (app or current_app).config.get('AJ_UPLOADS_ENDPOINT', 'uploads.uploaded_file')
