from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.extensions import db
from app.models.client import Conta
from app.models.product import Product
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.event import Event
from app.ntfy import notificar as ntfy_notificar
from datetime import datetime, timezone, date, time


def _clean(val):
    if not val:
        return None
    s = val.strip()
    if not s or s.lower() == "none":
        return None
    return s


def _save_event(obj, form):
    if not obj.event:
        event = Event()
        obj.event = event
        db.session.add(event)
        db.session.flush()
    event = obj.event
    event.tipo = _clean(form.get("evento_tipo"))
    event.tema = _clean(form.get("evento_tema"))
    event.obs = _clean(form.get("evento_complemento"))
    data_str = form.get("evento_data")
    event.data = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else None
    hora_str = form.get("evento_hora")
    event.hora = datetime.strptime(hora_str, "%H:%M").time() if hora_str else None
    event.local = _clean(form.get("evento_local"))
    conv_str = form.get("evento_convidados")
    event.convidados = int(conv_str) if conv_str else None
    event.cerimonial = _clean(form.get("evento_cerimonial"))
    return event


bp = Blueprint("orcamento", __name__)


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
    return render_template("orcamento/lista.html",
                           cliente=cliente, items=items)


@bp.route("/orcamento/remover/<int:id>", methods=["POST"])
def remover(id):
    items = session.get("orcamento_items", [])
    session["orcamento_items"] = [i for i in items if i["product_id"] != id]
    return redirect(url_for("orcamento.lista"))


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
        return redirect(url_for("orcamento.lista"))
    cliente = Conta.query.get(cliente_id)
    if not cliente:
        return redirect(url_for("orcamento.lista"))

    session_items = session.get("orcamento_items", [])
    if not session_items:
        return redirect(url_for("orcamento.lista"))

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
    return render_template("orcamento/confirmacao.html")
