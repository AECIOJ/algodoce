from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.ingredient import Ingredient
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.producao_insumo import ProducaoInsumo
from app.models.compra_item import CompraItem
from app.models.unit_conversion import UnitConversion
from app.constants import TIPO_INGREDIENTE, UND_INSUMO
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form, can_delete
from app.fields import FIELD_ID_SHORT, FIELD_NOME, FIELD_TIPO


INSUMOS_FIELDS = {
    'id':             FIELD_ID_SHORT,
    'nome':           {**FIELD_NOME, 'width': 18},
    'tipo':           {**FIELD_TIPO, 'width': 12, 'options': TIPO_INGREDIENTE},
    'unidade_medida': {'label': 'Und', 'width': 8, 'input': 'select', 'options': {u: u for u in UND_INSUMO}, 'required': True},
}

insumos_list = {'fields': INSUMOS_FIELDS, 'edit_endpoint': 'insumos.form'}


CONVERSOES_FIELDS = {'model': UnitConversion, 'type': 'table', 'template': 'sys_insumos/_conversions.html', 'fields': {
    'unidade': {'label': 'Unidade', 'input': 'select', 'options': {u: u for u in UND_INSUMO}},
    'fator':   { 'input': 'number'},
}}

PRODUTOS_FIELDS = {'model': ProductIngredient, 'type': 'table', 'template': 'sys_insumos/_produtos.html', 'readonly': True, 'fields': {
    'produto':    {'label': 'Produto'},
    'quantidade': {'label': 'Qtd'},
    'unidade':    {'label': 'Und'},
}}


def _insumos_pre_save(instance, request, is_new):
    UnitConversion.query.filter_by(ingredient_id=instance.id).delete()
    db.session.flush()
    unidades = request.form.getlist("conversion_unidade")
    fatores = request.form.getlist("conversion_fator")
    for un, fa in zip(unidades, fatores):
        if un and fa:
            db.session.add(UnitConversion(
                ingredient_id=instance.id, unidade=un, fator=fa,
            ))


insumos_form = {'model': Ingredient, 'redirect': 'insumos.list', 'entity_label': 'Insumo', 'page_scripts': 'sys_insumos/_form_scripts.html', 'fields': INSUMOS_FIELDS, 'sessions': {'Conversões': CONVERSOES_FIELDS, 'Produtos': PRODUTOS_FIELDS}, 'delete_when': {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion}, 'pre_save': _insumos_pre_save, 'flash_ok': 'Insumo cadastrado!', 'flash_update': 'Insumo atualizado!'}


bp = Blueprint("insumos", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/insumos")
def list():
    _list = List(**insumos_list)
    filter_config = build_filter_config(_list.fields)
    active = resolve_filters(filter_config, request.args)
    query = Ingredient.query.order_by(Ingredient.nome)
    insumos = query.all()
    linhas = insumos[:]
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_select_filter(linhas, 'tipo', active.get('tipo'), TIPO_INGREDIENTE)
    linhas = apply_select_filter(linhas, 'unidade_medida', active.get('unidade_medida'), {u: u for u in UND_INSUMO})
    insumos = linhas
    ctx = build_field_context(_list.fields)
    return render_template("sys_insumos/list.html", insumos=insumos, INSUMOS_LIST=_list, ctx=ctx, TIPO_INGREDIENTE=TIPO_INGREDIENTE, active_filters=active, FILTERS=filter_config)


@bp.route("/insumos/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/insumos/<int:id>/editar", methods=["GET", "POST"])
def form(id=None):
    products_using = []
    if id is not None:
        ingredient = Ingredient.query.get(id)
        if ingredient:
            products_using = (
                Product.query
                .join(ProductIngredient)
                .filter(ProductIngredient.ingredient_id == id)
                .order_by(Product.nome)
                .all()
            )
    return handle_form(insumos_form, id, extra_ctx={
        'products_using': products_using,
        'TIPO_INGREDIENTE': TIPO_INGREDIENTE,
        'UND_INSUMO': UND_INSUMO,
    })


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
