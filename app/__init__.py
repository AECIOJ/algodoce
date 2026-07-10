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
        r = requests.get("http://algodoce_pinggy:4040/api/tunnels", timeout=2)
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

    with app.app_context():
        from app.routes import sys_clients as contas, sys_products, sys_ingredients, sys_orders, sys_compras
        from app.routes import site, uploads, site_vitrine, site_orcamento
        from app.routes import sys_categories, sys_producao, sys_rubricas, sys_previsoes, sys_recursos, sys_a_pagar, sys_a_receber, sys_movimentos, sys_api, sys_orcamentos
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
        app.register_blueprint(sys_rubricas.bp)
        app.register_blueprint(sys_previsoes.bp)
        app.register_blueprint(sys_recursos.bp)
        app.register_blueprint(sys_a_pagar.bp)
        app.register_blueprint(sys_a_receber.bp)
        app.register_blueprint(sys_movimentos.bp)
        app.register_blueprint(sys_api.bp)
        app.register_blueprint(sys_orcamentos.bp)

        from app.routes.sys_carteira import bp as carteira_bp
        app.register_blueprint(carteira_bp)

        from app.models import client as conta_model, product, ingredient, product_ingredient, unit_conversion, order, category, quote, rubrica, transacao, previsao  # noqa
        from app.models.event import Event  # noqa
        from app.models.quote_item import QuoteItem  # noqa
        from app.models.compra import Compra  # noqa
        from app.models.compra_item import CompraItem  # noqa
        from app.models.order_item import OrderItem  # noqa
        from app.models.setting import Setting  # noqa
        from app.models.producao import Producao  # noqa
        from app.models.producao_insumo import ProducaoInsumo  # noqa
        from app.models.producao_produto import ProducaoProduto  # noqa
        from app.models.recurso import Recurso  # noqa
        from app.models.movto import Movto  # noqa
        from app.models.carteira import Carteira  # noqa

        from app.models.category import Category
        from app.models.client import Conta
        from app.models.product import Product
        from app.models.ingredient import Ingredient
        from app.models.quote import Quote
        from app.models.previsao import Previsao

        from app.fields import register_model
        register_model('category', Category)
        register_model('conta', Conta)
        register_model('product', Product)
        register_model('ingredient', Ingredient)
        register_model('quote', Quote)
        register_model('recurso', Recurso)
        register_model('producao', Producao)
        register_model('previsao', Previsao)
        register_model('movto', Movto)
        register_model('carteira', Carteira)

        for model_cls in [Category, Conta, Product, Ingredient, Quote, Recurso, Producao, Previsao, Movto, Carteira]:
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

    app.jinja_env.finalize = lambda x: '' if x is None else x

    app.jinja_env.filters['deep_attr'] = deep_attr
    app.jinja_env.filters['brl'] = fmt_brl
    app.jinja_env.filters['fmtid'] = fmt_id
    app.jinja_env.filters['fmtzero'] = fmt_zero
    app.jinja_env.filters['fmtzeroi'] = fmt_zero_int
    app.jinja_env.filters['fmtdate'] = fmt_date
    app.jinja_env.filters['fmtdatetime'] = fmt_datetime
    from app.fields import fields_to_columns, field_filter_options, field_grid, get_field
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

    return app
