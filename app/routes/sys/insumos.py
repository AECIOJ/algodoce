from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.ingredient import Ingredient
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.producao_insumo import ProducaoInsumo
from app.models.compra_item import CompraItem
from app.models.unit_conversion import UnitConversion
from app.constants import TIPO_INGREDIENTE, UND_INSUMO, PRODUCAO_ETAPAS
from app.form import handle_form, can_delete
from app.engine.handle_list import render_list


UND_MAP = {u: u for u in UND_INSUMO}

Entidade = {
    'Ingredient': {
        'id':              {'type': 'PK', 'width': 6},
        'nome':            {'type': 'TEXT', 'width': 18, 'transform': 'title'},
        'tipo':            {'type': 'LIST', 'width': 12, 'list': TIPO_INGREDIENTE},
        'unidade_medida':  {'type': 'LIST', 'width': 8, 'list': UND_MAP, 'required': True},
    },
    'UnitConversion': {
        'unidade':         {'type': 'LIST', 'list': UND_MAP, 'required': True,},
        'fator':           {'type': 'NUMBER', 'required': True, 'decimals': 6},
    },
    'ProductIngredient': {
        'product_id':      {'type': 'FK', 'label':'Produto', 'masterkey': 'product'},
        'quantidade':      {'type': 'NUMBER'},
        'unidade':         {'type': 'LIST', 'list': UND_MAP},
        'etapa':           {'type': 'LIST', 'list': PRODUCAO_ETAPAS},
    },
}

Lista = {
    'colunas': ['Ingredient'],
    'ordering': ['nome'],
    'new_endpoint': 'insumos.form',
    'edit_endpoint': 'insumos.form',
}


def _insumos_pre_save(instance, request, is_new):
    UnitConversion.query.filter_by(ingredient_id=instance.id).delete()
    db.session.flush()
    unidades = request.form.getlist("conversions_unidade[]")
    fatores = request.form.getlist("conversions_fator[]")
    for un, fa in zip(unidades, fatores):
        if un and fa:
            db.session.add(UnitConversion(
                ingredient_id=instance.id, unidade=un, fator=float(fa),
            ))


Form = {
    'fields': 'Ingredient',
    'sessions': {
        'Conversões': {'table': ['UnitConversion'], 'attr': 'conversions'},
        'Produtos': {'table': ['ProductIngredient'], 'attr': 'products', 'readonly': True},
    },
    'delete_when': {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion},
    'pre_save': _insumos_pre_save,
    'flash_ok': 'Insumo cadastrado!',
    'flash_update': 'Insumo atualizado!',
}


bp = Blueprint("insumos", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/insumos/")
@bp.route("/insumos")
def list():
    return render_list('Ingredient', __name__)


@bp.route("/insumos/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/insumos/<int:id>/editar", methods=["GET", "POST"])
def form(id=None):
    return handle_form(Form, id)


@bp.route("/insumos/<int:id>")
def detail(id):
    ingredient = Ingredient.query.get_or_404(id)

    query = Ingredient.query.with_entities(Ingredient.id).order_by(Ingredient.id)
    ids = [i.id for i in query.all()]

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

    products_using = (
        Product.query
        .join(ProductIngredient)
        .filter(ProductIngredient.ingredient_id == id)
        .order_by(Product.nome)
        .all()
    )

    return render_template(
        "sys_insumos/detail.html",
        ingredient=ingredient,
        nav=nav,
        products_using=products_using,
        TIPO_INGREDIENTE=TIPO_INGREDIENTE,
        can_delete=can_delete(ingredient, {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion}),
    )


@bp.route("/insumos/<int:id>/excluir", methods=["POST"])
def delete(id):
    ingredient = Ingredient.query.get_or_404(id)
    if not can_delete(ingredient, {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion}):
        flash(f"Não é possível excluir '{ingredient.nome}' — está em uso.", "danger")
        return redirect(url_for("insumos.detail", id=id))
    db.session.delete(ingredient)
    db.session.commit()
    flash("Insumo excluído!", "success")
    return redirect(url_for("insumos.list"))
