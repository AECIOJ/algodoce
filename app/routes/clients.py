from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models.client import Client
from app.models.order import Order

bp = Blueprint("clients", __name__)


@bp.route("/clientes")
def list():
    clients = Client.query.order_by(Client.nome).all()
    return render_template("clients/list.html", clients=clients)


@bp.route("/clientes/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    clients = (
        Client.query
        .filter(Client.nome.ilike(f"%{q}%"))
        .order_by(Client.nome)
        .limit(10)
        .all()
    )
    return jsonify([{"id": c.id, "nome": c.nome} for c in clients])


@bp.route("/clientes/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        client = Client(
            nome=request.form["nome"],
            email=request.form["email"],
            telefone=request.form.get("telefone", ""),
            endereco=request.form.get("endereco", ""),
        )
        db.session.add(client)
        db.session.commit()
        flash("Cliente cadastrado!", "success")
        return redirect(url_for("clients.list"))
    return render_template("clients/form.html")


@bp.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    client = Client.query.get_or_404(id)
    if request.method == "POST":
        client.nome = request.form["nome"]
        client.email = request.form["email"]
        client.telefone = request.form.get("telefone", "")
        client.endereco = request.form.get("endereco", "")
        db.session.commit()
        flash("Cliente atualizado!", "success")
        return redirect(url_for("clients.list"))

    query = Client.query.with_entities(Client.id).order_by(Client.id)
    ids = [c.id for c in query.all()]
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

    orders = client.orders.order_by(Order.data_pedido.desc()).all()
    return render_template("clients/form.html", client=client, nav=nav, orders=orders)


@bp.route("/clientes/<int:id>/toggle")
def toggle(id):
    client = Client.query.get_or_404(id)
    client.ativo = not client.ativo
    db.session.commit()
    flash("Cliente atualizado!", "success")
    return redirect(url_for("clients.edit", id=id))
