"""Instâncias das extensões Flask compartilhadas pelo projeto.

Ponto único de definição de `db`, `migrate` e `login_manager`. Substituiu o
antigo `app.extensions` (Fase 2 do PLANO.md); todas as dependências passam a
importar daqui.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
