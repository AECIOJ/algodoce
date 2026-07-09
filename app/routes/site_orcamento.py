from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.extensions import db
from app.models.client import Conta
from app.models.product import Product
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.event import Event
from app.ntfy import notificar as ntfy_notificar
from datetime import datetime, timezone, date, time
from app.utils import _clean, _save_event


bp = Blueprint("site_orcamento", __name__)


def _load_session_items():
    items = []
    for i in session.get("orcamento_items", []):
        produto = Product.query.get(i["product_id"])
        if produto:
            items.append({
                "product_id": i["product_id"],
                "produto": produto,
                "quantidade": i["quantidade"],
                "observacao": i["observacao"] or "",
            })
    return items


@bp.route("/orcamento")
def lista():
    cliente_id = session.get("cliente_id")
    cliente = None
    if cliente_id:
        cliente = Conta.query.get(cliente_id)
    items = _load_session_items()
    return render_template("site_orcamento/lista.html",
                           cliente=cliente, items=items)


@bp.route("/orcamento/remover/<int:id>", methods=["POST"])
def remover(id):
    items = session.get("orcamento_items", [])
    session["orcamento_items"] = [i for i in items if i["product_id"] != id]
    return redirect(url_for("site_orcamento.lista"))


@bp.route("/orcamento/atualizar-item", methods=["POST"])
def atualizar_item():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    if not product_id:
        return jsonify(error="product_id required"), 400
    items = session.get("orcamento_items", [])
    for i in items:
        if i["product_id"] == product_id:
            if "quantidade" in data:
                i["quantidade"] = int(data["quantidade"])
            if "observacao" in data:
                i["observacao"] = data["observacao"].strip() or None
            break
    session["orcamento_items"] = items
    return jsonify(success=True)


@bp.route("/api/cliente", methods=["POST"])
def identificar():
    data = request.get_json(silent=True) or {}
    telefone = data.get("telefone", "").strip()
    nome = data.get("nome", "").strip()

    if not telefone or not nome:
        return jsonify(error="Telefone e nome são obrigatórios"), 400

    cliente = Conta.query.filter_by(telefone=telefone).first()
    if not cliente:
        cliente = Conta(nome=nome, telefone=telefone, email=f"{telefone}@temp.com")
        cliente.ativo = True
        db.session.add(cliente)
        db.session.flush()
    else:
        cliente.nome = nome

    db.session.commit()
    session["cliente_id"] = cliente.id
    return jsonify(success=True, cliente_id=cliente.id)


@bp.route("/orcamento/enviar", methods=["POST"])
def enviar():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return redirect(url_for("site_orcamento.lista"))
    cliente = Conta.query.get(cliente_id)
    if not cliente:
        return redirect(url_for("site_orcamento.lista"))

    session_items = session.get("orcamento_items", [])
    if not session_items:
        return redirect(url_for("site_orcamento.lista"))

    quote = Quote(
        cliente_nome=cliente.nome,
        cliente_telefone=cliente.telefone,
        data_pedido=datetime.now(timezone.utc),
    )
    db.session.add(quote)
    db.session.flush()

    for i in session_items:
        item = QuoteItem(
            quote_id=quote.id,
            product_id=i["product_id"],
            quantidade=i["quantidade"],
            preco_unitario=None,
            observacao=i.get("observacao") or None,
        )
        db.session.add(item)

    _save_event(quote, request.form)

    db.session.commit()
    ntfy_notificar(quote)
    session.pop("orcamento_items", None)
    session.pop("cliente_id", None)
    return render_template("site_orcamento/confirmacao.html")


@bp.route("/api/orcamento-count")
def orcamento_count():
    items = session.get("orcamento_items", [])
    total = len(items)
    return jsonify(total=total)
