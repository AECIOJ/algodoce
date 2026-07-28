from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form


CARTEIRA_FIELDS = {
        'id': {'label': '#', 'width': 7, 'mask': '999'},
        'nome': {'width': 50},
        'uso': {'width': 10, 'options': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}, 'filter_options': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}},
        'gerar': {'width': 10, 'options': {0: 'Movimento', 1: 'Previsão'}, 'filter_options': {0: 'Movimento', 1: 'Previsão'}},
        'prazo_recebimento': {'label': 'Prazo', 'width': 5},
        'taxa_recebimento': {'label': 'Taxa', 'width': 8, 'input': 'number', 'align': 'right'},
}

carteira_list = {'fields': CARTEIRA_FIELDS, 'edit_endpoint': 'carteira.form'}


def _carteira_pre_save(instance, request, is_new):
    if not is_new:
        em_uso = bool(
            Compra.query.filter_by(carteira_id=instance.id).first()
            or Order.query.filter_by(carteira_id=instance.id).first()
            or Quote.query.filter_by(carteira_id=instance.id).first()
        )
        if em_uso:
            flash("Carteira já utilizada — não pode ser alterada. Crie uma nova.", "warning")
            return False
    return True


carteira_form = {'model': Carteira, 'redirect': 'carteira.list', 'entity_label': 'Carteira', 'form_tail': 'sys_carteira/_form_tail.html', 'page_scripts': 'sys_carteira/_page_scripts.html', 'fields': CARTEIRA_FIELDS, 'pre_save': _carteira_pre_save}


bp = Blueprint("carteira", __name__, url_prefix="/carteira")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    _list = List(**carteira_list)
    filter_config = build_filter_config(CARTEIRA_FIELDS)
    active = resolve_filters(filter_config, request.args)
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
    return render_template("sys_carteira/list.html", carteiras=carteiras, CARTEIRA_LIST=_list, ctx=ctx, active_filters=active, FILTERS=filter_config)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    extra = {}
    if id is not None:
        carteira = Carteira.query.get(id)
        if carteira:
            em_uso = bool(
                Compra.query.filter_by(carteira_id=id).first()
                or Order.query.filter_by(carteira_id=id).first()
                or Quote.query.filter_by(carteira_id=id).first()
            )
            extra['em_uso'] = em_uso
            if em_uso:
                extra['ro'] = True
    return handle_form(carteira_form, id, extra_ctx=extra)


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
        return redirect(url_for("carteira.form", id=id))
    db.session.delete(carteira)
    db.session.commit()
    flash("Carteira excluída!", "success")
    return redirect(url_for("carteira.list"))
