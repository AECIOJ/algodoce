from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models.ingredient import Ingredient
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.unit_conversion import UnitConversion

bp = Blueprint("ingredients", __name__)


@bp.route("/ingredientes")
def list():
    ingredients = Ingredient.query.order_by(Ingredient.nome).all()
    return render_template("ingredients/list.html", ingredients=ingredients)


@bp.route("/ingredientes/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        ingredient = Ingredient(
            nome=request.form["nome"],
            unidade_medida=request.form["unidade_medida"],
        )
        db.session.add(ingredient)
        db.session.commit()
        flash("Ingrediente cadastrado!", "success")
        return redirect(url_for("ingredients.list"))
    return render_template("ingredients/form.html")


@bp.route("/ingredientes/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    ingredient = Ingredient.query.get_or_404(id)
    if request.method == "POST":
        ingredient.nome = request.form["nome"]
        ingredient.unidade_medida = request.form["unidade_medida"]

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
        flash("Ingrediente atualizado!", "success")
        return redirect(url_for("ingredients.list"))

    query = Ingredient.query.with_entities(Ingredient.id).order_by(Ingredient.nome)
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
    )


@bp.route("/ingredientes/<int:id>")
def detail(id):
    ingredient = Ingredient.query.get_or_404(id)

    query = Ingredient.query.with_entities(Ingredient.id).order_by(Ingredient.nome)
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
    )


@bp.route("/ingredientes/<int:id>/uso")
def usage(id):
    qtd = ProductIngredient.query.filter_by(ingredient_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/ingredientes/<int:id>/excluir", methods=["POST"])
def delete(id):
    ingredient = Ingredient.query.get_or_404(id)

    usage = ProductIngredient.query.filter_by(ingredient_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{ingredient.nome}' — está em {usage} receita(s). "
            f"Remova o ingrediente das receitas primeiro.",
            "danger",
        )
        return redirect(url_for("ingredients.detail", id=id))

    UnitConversion.query.filter_by(ingredient_id=id).delete()
    db.session.delete(ingredient)
    db.session.commit()
    flash("Ingrediente excluído!", "success")
    return redirect(url_for("ingredients.list"))
