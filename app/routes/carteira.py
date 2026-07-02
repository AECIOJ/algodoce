from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote

bp = Blueprint("carteira", __name__, url_prefix="/carteira")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template("carteira/list.html", carteiras=carteiras)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        carteira = Carteira(
            nome=request.form["nome"].strip(),
            uso=request.form.get("uso", 1, type=int),
            gerar=request.form.get("gerar", 0, type=int),
            taxa_recebimento=request.form.get("taxa_recebimento", 0, type=float),
            prazo_recebimento=request.form.get("prazo_recebimento", "").strip() or None,
        )
        db.session.add(carteira)
        db.session.commit()
        flash("Carteira cadastrada!", "success")
        return redirect(url_for("carteira.list"))
    return render_template("carteira/form.html")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    carteira = Carteira.query.get_or_404(id)
    em_uso = bool(
        Compra.query.filter_by(carteira_id=id).first()
        or Order.query.filter_by(carteira_id=id).first()
        or Quote.query.filter_by(carteira_id=id).first()
    )
    if request.method == "POST":
        if em_uso:
            flash("Carteira já utilizada — não pode ser alterada. Crie uma nova.", "warning")
            return redirect(url_for("carteira.edit", id=id))
        carteira.nome = request.form["nome"].strip()
        carteira.uso = request.form.get("uso", 1, type=int)
        carteira.gerar = request.form.get("gerar", 0, type=int)
        carteira.taxa_recebimento = request.form.get("taxa_recebimento", 0, type=float)
        carteira.prazo_recebimento = request.form.get("prazo_recebimento", "").strip() or None
        db.session.commit()
        flash("Carteira atualizada!", "success")
        return redirect(url_for("carteira.list"))
    return render_template("carteira/form.html", carteira=carteira, em_uso=em_uso)


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    carteira = Carteira.query.get_or_404(id)
    em_uso = bool(
        Compra.query.filter_by(carteira_id=id).first()
        or Order.query.filter_by(carteira_id=id).first()
        or Quote.query.filter_by(carteira_id=id).first()
    )
    if em_uso:
        flash("Carteira em uso — não pode ser excluída.", "danger")
        return redirect(url_for("carteira.edit", id=id))
    db.session.delete(carteira)
    db.session.commit()
    flash("Carteira excluída!", "success")
    return redirect(url_for("carteira.list"))
