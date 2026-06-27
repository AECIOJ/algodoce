from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.forma_pagamento import FormaPagamento
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote

bp = Blueprint("forma_pagamento", __name__, url_prefix="/forma-pagamento")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    formas = FormaPagamento.query.order_by(FormaPagamento.nome).all()
    return render_template("forma_pagamento/list.html", formas=formas)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        forma = FormaPagamento(
            nome=request.form["nome"].strip(),
            uso=request.form.get("uso", 1, type=int),
            gerar=request.form.get("gerar", 0, type=int),
            taxa_recebimento=request.form.get("taxa_recebimento", 0, type=float),
            prazo_recebimento=request.form.get("prazo_recebimento", "").strip() or None,
        )
        db.session.add(forma)
        db.session.commit()
        flash("Forma de pagamento cadastrada!", "success")
        return redirect(url_for("forma_pagamento.list"))
    return render_template("forma_pagamento/form.html")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    forma = FormaPagamento.query.get_or_404(id)
    em_uso = bool(
        Compra.query.filter_by(forma_pagamento_id=id).first()
        or Order.query.filter_by(forma_pagamento_id=id).first()
        or Quote.query.filter_by(forma_pagamento_id=id).first()
    )
    if request.method == "POST":
        if em_uso:
            flash("Forma de pagamento já utilizada — não pode ser alterada. Crie uma nova.", "warning")
            return redirect(url_for("forma_pagamento.edit", id=id))
        forma.nome = request.form["nome"].strip()
        forma.uso = request.form.get("uso", 1, type=int)
        forma.gerar = request.form.get("gerar", 0, type=int)
        forma.taxa_recebimento = request.form.get("taxa_recebimento", 0, type=float)
        forma.prazo_recebimento = request.form.get("prazo_recebimento", "").strip() or None
        db.session.commit()
        flash("Forma de pagamento atualizada!", "success")
        return redirect(url_for("forma_pagamento.list"))
    return render_template("forma_pagamento/form.html", forma=forma, em_uso=em_uso)


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    forma = FormaPagamento.query.get_or_404(id)
    em_uso = bool(
        Compra.query.filter_by(forma_pagamento_id=id).first()
        or Order.query.filter_by(forma_pagamento_id=id).first()
        or Quote.query.filter_by(forma_pagamento_id=id).first()
    )
    if em_uso:
        flash("Forma de pagamento em uso — não pode ser excluída.", "danger")
        return redirect(url_for("forma_pagamento.edit", id=id))
    db.session.delete(forma)
    db.session.commit()
    flash("Forma de pagamento excluída!", "success")
    return redirect(url_for("forma_pagamento.list"))
