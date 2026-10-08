"""Acoplamento do framework com a aplicação host.

Ponto único de import das dependências específicas do projeto (SQLAlchemy db,
login manager, modelos Usuario/Configuracao, config APP) mais hooks opcionais de
markdown/túnel. Para portar o framework a outro host, ajustar este arquivo.
"""
from flask import current_app
from importlib.util import find_spec as _find_spec
from importlib import import_module as _import_module

from ajsystem.core.extensions import db, login_manager
from app.models.usuario import Usuario
from app.models.configuracao import Configuracao
from app.config import APP as _APP, Temas as _TEMAS
from ajsystem.defs.config import build_app, build_temas


def _override_ou(caminho, atributo, default):
    """Lê um override do host se o arquivo existir, senão o default.

    É o `if` declarativo do acoplamento: `find_spec` verifica a existência SEM
    executar nada; só havendo arquivo é que ele é importado. As três situações:

    - arquivo ausente → `default`, boot normal (host sem override);
    - arquivo presente → vale o atributo do host;
    - arquivo presente mas com erro interno → o erro original propaga. O
      `find_spec` distingue "não existe" de "existe e quebrou": um `except
      ImportError` genérico engoliria um typo dentro do arquivo e o boot
      seguiria com o default em silêncio — por isso não é usado aqui.
    - arquivo presente sem o atributo → `ImportError` nomeando o que falta.
      Silêncio aqui esconderia variável renomeada por engano; o motor é
      fail-fast com mensagem, não default silencioso.
    """
    if _find_spec(caminho) is None:
        return default
    mod = _import_module(caminho)
    if not hasattr(mod, atributo):
        raise ImportError(
            f"{caminho} existe mas não define {atributo!r} — declare o catálogo "
            f"ou apague o arquivo para valer o default do framework.")
    return getattr(mod, atributo)


# `version` vem no próprio dict (`APP['version']`, em `app/config.py`): o
# `build_app` valida o formato `1.aa.mm-build` e exibe como veio.
APP = build_app(_APP,
                botoes=_override_ou('app.extends.buttons', 'Buttons', {}),
                inputs=_override_ou('app.extends.inputs', 'Inputs', {}))
TEMAS = build_temas(_TEMAS)


def masks_override():
    """Catálogo de máscaras do host (`app.extends.masks.Masks`), se existir."""
    return _override_ou('app.extends.masks', 'Masks', {})

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
