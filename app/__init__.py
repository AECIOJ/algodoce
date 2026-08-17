import os
import threading
import time
from datetime import timedelta
import requests
from flask import Flask
from app.ajsystem.core.config import Config
from app.ajsystem.core.extensions import db, migrate, login_manager
from flask_migrate import upgrade
import sqlalchemy as sa

_tunnel_url = None
_tunnel_url_ts = 0
TUNNEL_TTL = 3300


def _fetch_tunnel_url():
    global _tunnel_url, _tunnel_url_ts
    try:
        r = requests.get("http://algodoce_cloudflare:4040/api/tunnels", timeout=2)
        data = r.json()
        for t in data.get("tunnels", []):
            u = t.get("public_url", "")
            if u.startswith("https://"):
                _tunnel_url = u
                _tunnel_url_ts = time.time()
                return
    except Exception:
        pass


def get_tunnel_url(force=False):
    global _tunnel_url, _tunnel_url_ts
    now = time.time()
    if force or _tunnel_url is None or (now - _tunnel_url_ts) > TUNNEL_TTL:
        _fetch_tunnel_url()
    return _tunnel_url or ""


def _bg_fetch_tunnel():
    time.sleep(3)
    _fetch_tunnel_url()


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    threading.Thread(target=_bg_fetch_tunnel, daemon=True).start()

    db.init_app(app)
    migrate.init_app(
        app,
        db,
        directory=os.path.join(os.path.dirname(__file__), "migrations"),
    )

    from app.models.user import User

    @app.after_request
    def no_static_cache(response):
        from flask import request
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    with app.app_context():
        # Import all models FIRST so mapper init resolves correctly
        from app.models import client as conta_model, product, ingredient, product_ingredient, unit_conversion, order, category, quote, operacao, transacao, previsao  # noqa
        from app.models.event import Event  # noqa
        from app.models.quote_item import QuoteItem  # noqa
        from app.models.compra import Compra  # noqa
        from app.models.compra_item import CompraItem  # noqa
        from app.models.compra_historico import CompraHistorico  # noqa
        from app.models.order_item import OrderItem  # noqa
        from app.models.setting import Setting  # noqa
        from app.models.producao import Producao  # noqa
        from app.models.producao_insumo import ProducaoInsumo  # noqa
        from app.models.producao_produto import ProducaoProduto  # noqa
        from app.models.recurso import Recurso  # noqa
        from app.models.movto import Movto  # noqa
        from app.models.trf import Trf  # noqa
        from app.models.carteira import Carteira  # noqa

        from app.models.category import Category
        from app.models.client import Conta
        from app.models.operacao import Operacao
        from app.models.product import Product
        from app.models.ingredient import Ingredient
        from app.models.quote import Quote
        from app.models.previsao import Previsao
        from app.models.product_ingredient import ProductIngredient
        from app.models.unit_conversion import UnitConversion

        from app.ajsystem.defs.entities import register_model

        from app.routes.sys import categorias, produtos, insumos, pedidos, compras, contas
        from app.routes.sys import producao, operacoes, recursos, transacao, movimentos
        from app.routes.sys import transferencias, orcamentos, relatorios, carteiras
        from app.routes import uploads

        app.register_blueprint(pedidos.bp)
        app.register_blueprint(compras.bp)
        app.register_blueprint(producao.bp)
        app.register_blueprint(recursos.bp)
        app.register_blueprint(transacao.bp)
        app.register_blueprint(movimentos.bp)
        app.register_blueprint(transferencias.bp)
        app.register_blueprint(relatorios.bp)
        app.register_blueprint(uploads.bp)

        from app.ajsystem import init_app
        init_app(app)

        from app.ajsystem.core import adapter
        adapter.set_tunnel_url_provider(lambda: get_tunnel_url(force=True))
        from app.content import render_pagina
        adapter.set_markdown_loader(render_pagina)

        register_model('category', Category)
        register_model('conta', Conta)
        register_model('operacao', Operacao)
        register_model('product', Product)
        register_model('ingredient', Ingredient)
        register_model('quote', Quote)
        register_model('recurso', Recurso)
        register_model('producao', Producao)
        register_model('previsao', Previsao)
        register_model('movto', Movto)
        register_model('recurso_trf', Trf)
        register_model('carteira', Carteira)
        register_model('quote_item', QuoteItem)
        register_model('event', Event)
        register_model('product_ingredient', ProductIngredient)
        register_model('unit_conversion', UnitConversion)

        try:
            upgrade()
        except Exception:
            pass

        Setting.ensure_keys()

        for seq, tbl in [('quotes_id_seq', 'quotes'), ('orders_id_seq', 'orders'), ('compras_id_seq', 'compras')]:
            try:
                db.session.execute(
                    sa.text(f"SELECT setval('{seq}', COALESCE((SELECT MAX(id) FROM {tbl}), 1))")
                )
            except Exception:
                db.session.rollback()
        db.session.commit()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username)
            db.session.add(admin)
        admin.set_password(admin_password)
        db.session.commit()

    app.jinja_env.policies['json.dumps_kwargs'] = {'sort_keys': False}
    app.jinja_env.finalize = lambda x: 'Sim' if x is True else 'Não' if x is False else '' if x is None else x

    @app.context_processor
    def inject_globals():
        from datetime import date
        from flask import request
        host = request.host.split(':')[0]
        qr_enabled = host in ('localhost', '127.0.0.1', '::1')
        return dict(tunnel_url=get_tunnel_url(), qr_enabled=qr_enabled, timedelta=timedelta, hoje=date.today())

    @app.context_processor
    def inject_versao():
        from flask_login import current_user
        from app.ajsystem.core.adapter import APP
        usuario = (current_user.username if current_user.is_authenticated else "Visitante").upper()
        return dict(versao=APP.version or '', usuario=usuario)

    def tema_atual():
        from app.ajsystem.core.adapter import APP, TEMAS
        nome = APP.tema or next(iter(TEMAS))
        if nome not in TEMAS:
            nome = next(iter(TEMAS))
        return nome

    @app.context_processor
    def inject_app_config():
        import json
        from app.ajsystem.core.adapter import APP, TEMAS
        from app.ajsystem.core.menu import modulo_atual, menus_para_json
        tema_nome = tema_atual()
        return {
            'APP': APP,
            'TEMA': TEMAS[tema_nome],
            'TEMAS': TEMAS,
            'TEMA_NOME': tema_nome,
            'modulo': modulo_atual(),
            'modulo_menus_json': json.dumps(menus_para_json()),
        }

    @app.context_processor
    def inject_site_categories():
        from app.models.category import Category
        cats = Category.query.filter_by(ativo=True).order_by(Category.ordem).all()
        return dict(site_categories=cats)

    @app.context_processor
    def inject_buttons():
        from app.ajsystem.defs.buttons import (
            BTN_SALVAR, BTN_ENVIAR, BTN_EXCLUIR, BTN_NOVO, BTN_VOLTAR,
            BTN_EDITAR, BTN_CANCELAR, BTN_CONVERTER, BTN_LISTA,
            BTN_IMPRIMIR, BTN_DETALHES, BTN_ADICIONAR, BTN_ADICIONAR_ITEM,
            BTN_FINALIZAR, BTN_ATUALIZAR, BTN_REMOVER, BTN_SIM, BTN_NAO,
            BTN_LIMPAR, BTN_APLICAR, BTN_OK, BTN_SAIR, BTN_RENOVAR,
            BTN_RELATORIO, BTN_GERAR, BTN_CONFIRMAR, BTN_EDITAR_PRODUTO,
            BTN_ENTRAR, BTN_ACESSAR, Button, ConfirmModal,
            CONFIRM_EXCLUIR, CONFIRM_REMOVER_ITEM,
        )
        return dict(
            BTN_SALVAR=BTN_SALVAR, BTN_ENVIAR=BTN_ENVIAR, BTN_EXCLUIR=BTN_EXCLUIR,
            BTN_NOVO=BTN_NOVO, BTN_VOLTAR=BTN_VOLTAR, BTN_EDITAR=BTN_EDITAR,
            BTN_CANCELAR=BTN_CANCELAR, BTN_CONVERTER=BTN_CONVERTER,
            BTN_LISTA=BTN_LISTA, BTN_IMPRIMIR=BTN_IMPRIMIR,
            BTN_DETALHES=BTN_DETALHES, BTN_ADICIONAR=BTN_ADICIONAR,
            BTN_ADICIONAR_ITEM=BTN_ADICIONAR_ITEM, BTN_FINALIZAR=BTN_FINALIZAR,
            BTN_ATUALIZAR=BTN_ATUALIZAR, BTN_REMOVER=BTN_REMOVER,
            BTN_SIM=BTN_SIM, BTN_NAO=BTN_NAO,
            BTN_LIMPAR=BTN_LIMPAR, BTN_APLICAR=BTN_APLICAR,
            BTN_OK=BTN_OK, BTN_SAIR=BTN_SAIR, BTN_RENOVAR=BTN_RENOVAR,
            BTN_RELATORIO=BTN_RELATORIO, BTN_GERAR=BTN_GERAR,
            BTN_CONFIRMAR=BTN_CONFIRMAR, BTN_EDITAR_PRODUTO=BTN_EDITAR_PRODUTO,
            BTN_ENTRAR=BTN_ENTRAR, BTN_ACESSAR=BTN_ACESSAR,
            Button=Button, ConfirmModal=ConfirmModal,
            CONFIRM_EXCLUIR=CONFIRM_EXCLUIR, CONFIRM_REMOVER_ITEM=CONFIRM_REMOVER_ITEM,
        )

    @app.after_request
    def cache_static(response):
        from flask import request as _r
        if _r.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    return app
