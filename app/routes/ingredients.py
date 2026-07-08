from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.ingredient import Ingredient
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.unit_conversion import UnitConversion
from app.constants import TIPO_INGREDIENTE
from app.fields import Field, build_field_context


INGREDIENTS_FIELDS = [
    Field(name='id', label='#', width=3, mask='999'),
    Field(name='nome', label='Nome', width=18),
    Field(name='tipo', label='Tipo', width=12, options=TIPO_INGREDIENTE, filter_options=list(TIPO_INGREDIENTE.values())),
    Field(name='unidade_medida', label='Und', width=8),
]

bp = Blueprint("ingredients", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/insumos")
def list():
    filtro_tipo = request.args.get("tipo", "todos")
    query = Ingredient.query.order_by(Ingredient.nome)
    if filtro_tipo != "todos":
        query = query.filter_by(tipo=int(filtro_tipo))
    ingredients = query.all()
    ctx = build_field_context(INGREDIENTS_FIELDS)
    return render_template("ingredients/list.html", ingredients=ingredients, fields=INGREDIENTS_FIELDS, ctx=ctx, TIPO_INGREDIENTE=TIPO_INGREDIENTE)


@bp.route("/insumos/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        ingredient = Ingredient(
            nome=request.form["nome"],
            unidade_medida=request.form["unidade_medida"],
            tipo=request.form.get("tipo", 0, type=int),
        )
        db.session.add(ingredient)
        db.session.commit()
        flash("Insumo cadastrado!", "success")
        return redirect(url_for("ingredients.list"))
    return render_template("ingredients/form.html", TIPO_INGREDIENTE=TIPO_INGREDIENTE)


@bp.route("/insumos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    ingredient = Ingredient.query.get(id)
    if not ingredient:
        flash("Código inexistente", "warning")
        return redirect(url_for("ingredients.list"))
    if request.method == "POST":
        ingredient.nome = request.form["nome"]
        ingredient.unidade_medida = request.form["unidade_medida"]
        ingredient.tipo = request.form.get("tipo", 0, type=int)

        UnitConversion.query.filter_by(ingredient_id=ingredient.id).delete()
        db.session.flush()

        unidades = request.form.getlist("conversion_unidade")
        fatores = request.form.getlist("conversion_fator")
        for un, fa in zip(unidades, fatores):
            if un and fa:
                db.session.add(UnitConversion(
                    ingredient_id=ingredient.id,
                    unidade=un,
                    fator=fa,
                ))

        db.session.commit()
        flash("Insumo atualizado!", "success")
        return redirect(url_for("ingredients.list"))

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
        "ingredients/form.html",
        ingredient=ingredient,
        nav=nav,
        products_using=products_using,
        TIPO_INGREDIENTE=TIPO_INGREDIENTE,
    )


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
        "ingredients/detail.html",
        ingredient=ingredient,
        nav=nav,
        products_using=products_using,
        TIPO_INGREDIENTE=TIPO_INGREDIENTE,
    )


@bp.route("/insumos/<int:id>/uso")
def usage(id):
    qtd = ProductIngredient.query.filter_by(ingredient_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/insumos/<int:id>/excluir", methods=["POST"])
def delete(id):
    ingredient = Ingredient.query.get_or_404(id)

    usage = ProductIngredient.query.filter_by(ingredient_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{ingredient.nome}' — está em {usage} receita(s). "
            f"Remova o insumo das receitas primeiro.",
            "danger",
        )
        return redirect(url_for("ingredients.detail", id=id))

    UnitConversion.query.filter_by(ingredient_id=id).delete()
    db.session.delete(ingredient)
    db.session.commit()
    flash("Insumo excluído!", "success")
    return redirect(url_for("ingredients.list"))
