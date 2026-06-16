from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.extensions import db
from app.models.client import Conta
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


@bp.route("/orcamento")
def lista():
    cliente_id = session.get("cliente_id")
    cliente = None
    items = []
    quote = None
    if cliente_id:
        cliente = Conta.query.get(cliente_id)
        if cliente:
            quote = Quote.query.filter_by(
                cliente_telefone=cliente.telefone, status=0
            ).order_by(Quote.id.desc()).first()
            if quote:
                items = QuoteItem.query.filter_by(quote_id=quote.id).all()
    return render_template("orcamento/lista.html",
                           cliente=cliente, items=items, quote=quote)


@bp.route("/orcamento/remover/<int:id>", methods=["POST"])
def remover(id):
    item = QuoteItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for("orcamento.lista"))


@bp.route("/orcamento/atualizar/<int:id>", methods=["POST"])
def atualizar(id):
    item = QuoteItem.query.get_or_404(id)
    data = request.form

    if "quantidade" in data:
        try:
            nova_qtd = int(data["quantidade"])
            minima = item.product.qtd_minima or 1
            if nova_qtd >= minima:
                item.quantidade = nova_qtd
        except (ValueError, TypeError):
            pass

    if "observacao" in data:
        item.observacao = data["observacao"].strip() or None

    db.session.commit()
    return redirect(url_for("orcamento.lista"))


@bp.route("/orcamento/salvar", methods=["POST"])
def salvar_tudo():
    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return redirect(url_for("orcamento.lista"))

    cliente = Conta.query.get(cliente_id)
    if not cliente:
        return redirect(url_for("orcamento.lista"))

    quote = Quote.query.filter_by(
        cliente_telefone=cliente.telefone, status=0
    ).order_by(Quote.id.desc()).first()
    if not quote:
        return redirect(url_for("orcamento.lista"))

    items = QuoteItem.query.filter_by(quote_id=quote.id).all()
    for item in items:
        qtd_key = f"quantidade_{item.id}"
        obs_key = f"observacao_{item.id}"

        if qtd_key in request.form:
            try:
                nova_qtd = int(request.form[qtd_key])
                minima = item.product.qtd_minima or 1
                if nova_qtd >= minima:
                    item.quantidade = nova_qtd
            except (ValueError, TypeError):
                pass

        if obs_key in request.form:
            item.observacao = request.form[obs_key].strip() or None

    db.session.commit()
    return redirect(url_for("orcamento.lista"))


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

    quote = Quote.query.filter_by(
        cliente_telefone=cliente.telefone, status=0
    ).order_by(Quote.id.desc()).first()

    if not quote:
        return redirect(url_for("orcamento.lista"))

    _save_event(quote, request.form)

    db.session.commit()
    ntfy_notificar(quote)
    session.pop("cliente_id", None)
    return render_template("orcamento/confirmacao.html")
