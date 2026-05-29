from flask import Flask
from app.config import Config
from app.extensions import db, migrate
from flask_migrate import upgrade


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from app.routes import clients, products, ingredients, orders, reports

        app.register_blueprint(clients.bp)
        app.register_blueprint(products.bp)
        app.register_blueprint(ingredients.bp)
        app.register_blueprint(orders.bp)
        app.register_blueprint(reports.bp)

        from app.models import client, product, ingredient, product_ingredient, unit_conversion, order, order_item  # noqa

        upgrade()

    return app
