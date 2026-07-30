from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote
from app.form import handle_form
from app.engine.handle_list import render_list


Entidade = {
    'Carteira': {
        'id':                 {'type': 'PK', 'width': 6},
        'nome':               {'type': 'TEXT', 'width': 50, 'transform': 'title'},
        'uso':                {'type': 'LIST', 'width': 10, 'list': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}},
        'gerar':              {'type': 'LIST', 'width': 10, 'list': {0: 'Movimento', 1: 'Previsão'}},
        'prazo_recebimento':  {'type': 'INT', 'width': 5},
        'taxa_recebimento':   {'type': 'NUMBER', 'width': 8},
    },
}

Lista = {
    'colunas': ['Carteira'],
    'ordering': ['nome'],
    'new_endpoint': 'carteira.form',
    'edit_endpoint': 'carteira.form',
}


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


Form = {
    'fields': 'Carteira',
    'form_tail': 'sys_carteira/_form_tail.html',
    'page_scripts': 'sys_carteira/_page_scripts.html',
    'pre_save': _carteira_pre_save,
}


bp = Blueprint("carteira", __name__, url_prefix="/carteira")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    return render_list('Carteira', __name__)


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
    return handle_form(Form, id, extra_ctx=extra)


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
