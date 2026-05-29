from datetime import date, datetime, timezone
from urllib.request import urlopen
from urllib.error import URLError
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import func
from app.extensions import db
from app.models.client import Client
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem

bp = Blueprint("orders", __name__)


@bp.route("/ngrok-url")
def ngrok_url():
    try:
        resp = urlopen("http://ngrok:4040/api/tunnels", timeout=3)
        data = json.loads(resp.read())
        urls = [t["public_url"] for t in data["tunnels"] if t["proto"] == "https"]
        return jsonify({"url": urls[0] if urls else None})
    except (URLError, KeyError, IndexError):
        return jsonify({"url": None})


@bp.route("/")
def dashboard():
    hoje = date.today()
    orders = Order.query.order_by(Order.data_entrega).all()

    grupos = {}
    for o in orders:
        grupos.setdefault(o.status, []).append(o)

    ordem_status = ["pendente", "em_producao", "pronto", "entregue", "cancelado"]
    grupos_ordenados = {s: grupos.get(s, []) for s in ordem_status}

    return render_template("orders/dashboard.html", grupos=grupos_ordenados, hoje=hoje)


@bp.route("/pedidos")
def list():
    orders = Order.query.order_by(Order.data_entrega).all()
    return render_template("orders/list.html", orders=orders)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        client_id = request.form["client_id"]
        data_entrega = datetime.strptime(
            request.form["data_entrega"], "%Y-%m-%d"
        ).date()
        observacao = request.form.get("observacao", "")

        order = Order(
            client_id=client_id,
            data_entrega=data_entrega,
            observacao=observacao,
        )
        db.session.add(order)
        db.session.flush()

        produtos = request.form.getlist("product_id")
        quantidades = request.form.getlist("quantidade")
        total = 0
        for pid, qtd in zip(produtos, quantidades):
            if not pid or not qtd:
                continue
            product = Product.query.get(int(pid))
            qtd_val = float(qtd)
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantidade=qtd_val,
                preco_unitario=product.preco,
            )
            db.session.add(item)
            total += float(product.preco) * qtd_val

        order.total = total
        db.session.commit()
        flash("Pedido criado!", "success")
        return redirect(url_for("orders.list"))

    clients = Client.query.filter_by(ativo=True).order_by(Client.nome).all()
    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    return render_template(
        "orders/form.html", clients=clients, products=products
    )


@bp.route("/pedidos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    order = Order.query.get_or_404(id)
    if request.method == "POST":
        order.client_id = request.form["client_id"]
        order.data_entrega = datetime.strptime(
            request.form["data_entrega"], "%Y-%m-%d"
        ).date()
        order.observacao = request.form.get("observacao", "")
        order.status = request.form.get("status", order.status)

        OrderItem.query.filter_by(order_id=order.id).delete()

        produtos = request.form.getlist("product_id")
        quantidades = request.form.getlist("quantidade")
        total = 0
        for pid, qtd in zip(produtos, quantidades):
            if not pid or not qtd:
                continue
            product = Product.query.get(int(pid))
            qtd_val = float(qtd)
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantidade=qtd_val,
                preco_unitario=product.preco,
            )
            db.session.add(item)
            total += float(product.preco) * qtd_val

        order.total = total
        db.session.commit()
        flash("Pedido atualizado!", "success")
        return redirect(url_for("orders.edit", id=id))

    clients = Client.query.filter_by(ativo=True).order_by(Client.nome).all()
    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()

    query = Order.query.with_entities(Order.id).order_by(Order.id)
    ids = [o.id for o in query.all()]
    try:
        current_idx = ids.index(id)
        nav = {
            "first_id": ids[0],
            "last_id": ids[-1],
            "prev_id": ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": ids[current_idx + 1] if current_idx < len(ids) - 1 else None,
        }
    except ValueError:
        nav = {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}

    return render_template(
        "orders/form.html", order=order, clients=clients, products=products, nav=nav
    )


@bp.route("/pedidos/<int:id>/status", methods=["POST"])
def status(id):
    order = Order.query.get_or_404(id)
    novo_status = request.form["status"]
    if novo_status in ["pendente", "em_producao", "pronto", "entregue"]:
        order.status = novo_status
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("orders.edit", id=id))


@bp.route("/pedidos/<int:id>/cancelar", methods=["POST"])
def cancel(id):
    order = Order.query.get_or_404(id)
    order.status = "cancelado"
    db.session.commit()
    flash("Pedido cancelado!", "success")
    return redirect(url_for("orders.edit", id=id))
