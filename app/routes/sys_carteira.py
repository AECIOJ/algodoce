from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, MODE_NUMBER, MODE_TEXT, MODE_SELECT
from app.table import Field, build_field_context, Table


CARTEIRA_FIELDS = [
    Field(name='id', label='#', width=7, mask='999'),
    Field(name='nome', label='Nome', width=50),
    Field(name='uso', label='Uso', width=10, options={0: 'Pedido', 1: 'Ambos', 2: 'Compra'}, filter_options={0: 'Pedido', 1: 'Ambos', 2: 'Compra'}),
    Field(name='gerar', label='Gerar', width=10, options={0: 'Movimento', 1: 'Previsão'}, filter_options={0: 'Movimento', 1: 'Previsão'}),
    Field(name='prazo_recebimento', label='Prazo', width=5),
    Field(name='taxa_recebimento', label='Taxa', width=8, input='number', align='right'),
]

CARTEIRA_TABLE = Table(fields=CARTEIRA_FIELDS, edit_endpoint='carteira.edit')

CARTEIRA_FILTERS = {
    'id':                MODE_NUMBER,
    'nome':              MODE_TEXT,
    'uso':               {**MODE_SELECT, 'options': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}},
    'gerar':             {**MODE_SELECT, 'options': {0: 'Movimento', 1: 'Previsão'}},
    'prazo_recebimento': MODE_TEXT,
    'taxa_recebimento':  MODE_NUMBER,
}

bp = Blueprint("carteira", __name__, url_prefix="/carteira")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    active = resolve_filters(CARTEIRA_FILTERS, request.args)
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    linhas = carteiras[:]
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_select_filter(linhas, 'uso', active.get('uso'), {0: 'Pedido', 1: 'Ambos', 2: 'Compra'})
    linhas = apply_select_filter(linhas, 'gerar', active.get('gerar'), {0: 'Movimento', 1: 'Previsão'})
    linhas = apply_text_filter(linhas, 'prazo_recebimento', active.get('prazo_recebimento'))
    linhas = apply_number_filter(linhas, 'taxa_recebimento', active.get('taxa_recebimento'))
    carteiras = linhas
    ctx = build_field_context(CARTEIRA_FIELDS)
    return render_template("sys_carteira/list.html", carteiras=carteiras, CARTEIRA_TABLE=CARTEIRA_TABLE, ctx=ctx, active_filters=active, FILTERS=CARTEIRA_FILTERS)


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
    return render_template("sys_carteira/form.html")


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
    return render_template("sys_carteira/form.html", carteira=carteira, em_uso=em_uso)


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
