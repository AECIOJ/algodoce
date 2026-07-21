import os
import threading
import time
from datetime import timedelta
import requests
from flask import Flask
from app.config import Config
from app.extensions import db, migrate, login_manager
from flask_migrate import upgrade
import sqlalchemy as sa

from app.utils import fmt_brl, fmt_id, fmt_zero, fmt_zero_int, fmt_date, fmt_datetime, aplicar_transformacao, deep_attr

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
    login_manager.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import redirect, url_for
        return redirect(url_for('site.index'))

    import time as _time

    @app.before_request
    def check_session_timeout():
        from flask import redirect, url_for, session, request as _req, current_app
        from flask_login import current_user, logout_user
        if current_app.config.get('SESSION_TIMEOUT', 0) <= 0:
            return
        if not current_user.is_authenticated:
            return
        if _req.endpoint in ('auth.keepalive',):
            return
        now = _time.time()
        last = session.get('_last_activity')
        timeout = current_app.config['SESSION_TIMEOUT'] * 60
        if last and (now - last) > timeout:
            logout_user()
            session.clear()
            return redirect(url_for('site.index'))
        session['_last_activity'] = now

    @app.after_request
    def no_static_cache(response):
        from flask import request
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
        return response

    with app.app_context():
        from app.routes import sys_clients as contas, sys_products, sys_ingredients, sys_orders, sys_compras
        from app.routes import site, uploads, site_vitrine, site_orcamento
        from app.routes import sys_categories, sys_producao, sys_operacoes, sys_previsoes, sys_recursos, sys_transacao, sys_movimentos, sys_transferencias, sys_api, sys_orcamentos
        from app.routes.sys_auth import bp as auth, bp_seguranca as seguranca

        app.register_blueprint(contas.bp)
        app.register_blueprint(sys_products.bp)
        app.register_blueprint(sys_ingredients.bp)
        app.register_blueprint(sys_orders.bp)
        app.register_blueprint(sys_compras.bp)
        app.register_blueprint(auth)
        app.register_blueprint(site.bp)
        app.register_blueprint(uploads.bp)
        app.register_blueprint(site_vitrine.bp)
        app.register_blueprint(site_orcamento.bp)
        app.register_blueprint(sys_categories.bp)
        app.register_blueprint(seguranca)
        app.register_blueprint(sys_producao.bp)
        app.register_blueprint(sys_operacoes.bp)
        app.register_blueprint(sys_previsoes.bp)
        app.register_blueprint(sys_recursos.bp)
        app.register_blueprint(sys_transacao.bp)
        app.register_blueprint(sys_movimentos.bp)
        app.register_blueprint(sys_transferencias.bp)
        app.register_blueprint(sys_api.bp)
        app.register_blueprint(sys_orcamentos.bp)

        from app.routes.sys_carteira import bp as carteira_bp
        app.register_blueprint(carteira_bp)

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
        from app.models.product import Product
        from app.models.ingredient import Ingredient
        from app.models.quote import Quote
        from app.models.previsao import Previsao

        from app.table import register_model
        register_model('category', Category)
        register_model('conta', Conta)
        register_model('product', Product)
        register_model('ingredient', Ingredient)
        register_model('quote', Quote)
        register_model('recurso', Recurso)
        register_model('producao', Producao)
        register_model('previsao', Previsao)
        register_model('movto', Movto)
        register_model('recurso_trf', Trf)
        register_model('carteira', Carteira)

        for model_cls in [Category, Conta, Product, Ingredient, Quote, Recurso, Producao, Previsao, Movto, Trf, Carteira]:
            sa.event.listen(model_cls, 'before_insert', aplicar_transformacao)
            sa.event.listen(model_cls, 'before_update', aplicar_transformacao)

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

    app.jinja_env.filters['deep_attr'] = deep_attr
    app.jinja_env.filters['brl'] = fmt_brl
    app.jinja_env.filters['fmtid'] = fmt_id
    app.jinja_env.filters['fmtzero'] = fmt_zero
    app.jinja_env.filters['fmtzeroi'] = fmt_zero_int
    app.jinja_env.filters['fmtdate'] = fmt_date
    app.jinja_env.filters['fmtdatetime'] = fmt_datetime
    from app.table import fields_to_columns, field_filter_options, field_grid, get_field
    app.jinja_env.filters['fields_to_columns'] = fields_to_columns
    app.jinja_env.filters['field_filter_options'] = field_filter_options
    app.jinja_env.filters['field_grid'] = field_grid
    app.jinja_env.globals['get_field'] = get_field

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
        import importlib.util
        import os
        import sys
        versao_path = os.path.join(app.root_path, "versao.py")
        spec = importlib.util.spec_from_file_location("__versao__", versao_path)
        vmod = importlib.util.module_from_spec(spec)
        sys.modules["__versao__"] = vmod
        spec.loader.exec_module(vmod)
        ano = vmod.YEAR[-2:]
        mes = vmod.MONTH
        seq = vmod.SEQUENCE
        versao = f"v1.{ano}.{mes}-{seq}"
        usuario = (current_user.username if current_user.is_authenticated else "Visitante").upper()
        return dict(versao=versao, usuario=usuario)

    @app.context_processor
    def inject_site_categories():
        from app.models.category import Category
        cats = Category.query.filter_by(ativo=True).order_by(Category.ordem).all()
        return dict(site_categories=cats)

    @app.context_processor
    def inject_buttons():
        from app.buttons import (
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
