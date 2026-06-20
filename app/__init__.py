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

from app.utils import fmt_brl, fmt_id, fmt_zero, fmt_zero_int

_ngrok_url = None


def _fetch_ngrok_url():
    global _ngrok_url
    try:
        r = requests.get("http://algodoce_ngrok:4040/api/tunnels", timeout=2)
        data = r.json()
        for t in data.get("tunnels", []):
            u = t.get("public_url", "")
            if u.startswith("https://"):
                _ngrok_url = u
                return
    except Exception:
        pass


def get_ngrok_url():
    if _ngrok_url is None:
        _fetch_ngrok_url()
    return _ngrok_url or ""


def _bg_fetch_ngrok():
    time.sleep(3)
    _fetch_ngrok_url()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    threading.Thread(target=_bg_fetch_ngrok, daemon=True).start()

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
        from app.routes import clients as contas, products, ingredients, orders, reports
        from app.routes import auth, site, uploads, vitrine, orcamento, categories, seguranca, producao

        app.register_blueprint(contas.bp)
        app.register_blueprint(products.bp)
        app.register_blueprint(ingredients.bp)
        app.register_blueprint(orders.bp)
        app.register_blueprint(reports.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(site.bp)
        app.register_blueprint(uploads.bp)
        app.register_blueprint(vitrine.bp)
        app.register_blueprint(orcamento.bp)
        app.register_blueprint(categories.bp)
        app.register_blueprint(seguranca.bp)
        app.register_blueprint(producao.bp)

        from app.models import client as conta_model, product, ingredient, product_ingredient, unit_conversion, order, category, quote  # noqa
        from app.models.event import Event  # noqa
        from app.models.quote_item import QuoteItem  # noqa
        from app.models.order_item import OrderItem  # noqa
        from app.models.setting import Setting  # noqa
        from app.models.producao import Producao  # noqa
        from app.models.producao_insumo import ProducaoInsumo  # noqa
        from app.models.producao_produto import ProducaoProduto  # noqa

        upgrade()

        Setting.ensure_keys()

        db.session.execute(
            sa.text("SELECT setval('quotes_id_seq', COALESCE((SELECT MAX(id) FROM quotes), 1))")
        )
        db.session.execute(
            sa.text("SELECT setval('orders_id_seq', COALESCE((SELECT MAX(id) FROM orders), 1))")
        )
        db.session.commit()

        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username)
            db.session.add(admin)
        admin.set_password(admin_password)
        db.session.commit()

    app.jinja_env.filters['brl'] = fmt_brl
    app.jinja_env.filters['fmtid'] = fmt_id
    app.jinja_env.filters['fmtzero'] = fmt_zero
    app.jinja_env.filters['fmtzeroi'] = fmt_zero_int

    @app.context_processor
    def inject_globals():
        return dict(ngrok_url=get_ngrok_url(), timedelta=timedelta)

    @app.context_processor
    def inject_site_categories():
        from app.models.category import Category
        cats = Category.query.filter_by(ativo=True).order_by(Category.ordem).all()
        return dict(site_categories=cats)

    return app
