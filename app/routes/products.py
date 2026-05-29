import os
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app, jsonify
)
from app.extensions import db
from app.models.product import Product
from app.models.ingredient import Ingredient
from app.models.product_ingredient import ProductIngredient
from app.models.order_item import OrderItem

bp = Blueprint("products", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/produtos")
def list():
    products = Product.query.order_by(Product.nome).all()
    return render_template("products/list.html", products=products)


@bp.route("/produtos/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        product = Product(
            nome=request.form["nome"],
            descricao=request.form.get("descricao", ""),
            preco=request.form["preco"],
            unidade=request.form.get("unidade", "cento"),
        )
        db.session.add(product)
        db.session.flush()

        _handle_imagem(request, product)

        ingredientes = _parse_ingredients(request)
        for ing_id, qtd, un in ingredientes:
            pi = ProductIngredient(
                product_id=product.id,
                ingredient_id=ing_id,
                quantidade=qtd,
                unidade=un,
            )
            db.session.add(pi)

        db.session.commit()
        flash("Produto cadastrado!", "success")
        return redirect(url_for("products.list"))

    ingredients = Ingredient.query.order_by(Ingredient.nome).all()
    return render_template("products/form.html", ingredients=ingredients)


@bp.route("/produtos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    product = Product.query.get_or_404(id)
    if request.method == "POST":
        product.nome = request.form["nome"]
        product.descricao = request.form.get("descricao", "")
        product.preco = request.form["preco"]
        product.unidade = request.form.get("unidade", "cento")

        if request.form.get("remover_imagem"):
            _remove_imagem(product)
        else:
            _handle_imagem(request, product)

        ProductIngredient.query.filter_by(product_id=product.id).delete()
        db.session.flush()

        ingredientes = _parse_ingredients(request)
        for ing_id, qtd, un in ingredientes:
            pi = ProductIngredient(
                product_id=product.id,
                ingredient_id=ing_id,
                quantidade=qtd,
                unidade=un,
            )
            db.session.add(pi)

        db.session.commit()
        flash("Produto atualizado!", "success")
        return redirect(url_for("products.list"))

    ingredients = Ingredient.query.order_by(Ingredient.nome).all()

    query = Product.query.with_entities(Product.id).order_by(Product.id)
    ids = [p.id for p in query.all()]
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

    return render_template(
        "products/form.html", product=product, ingredients=ingredients, nav=nav
    )


@bp.route("/produtos/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    products = (
        Product.query
        .filter(Product.nome.ilike(f"%{q}%"))
        .order_by(Product.nome)
        .limit(10)
        .all()
    )
    return jsonify([{"id": p.id, "nome": p.nome} for p in products])


@bp.route("/produtos/<int:id>")
def detail(id):
    product = Product.query.get_or_404(id)
    ativos = request.args.get("ativos", "1") == "1"

    query = Product.query.with_entities(Product.id).order_by(Product.id)
    if ativos:
        query = query.filter(Product.ativo == True)
    ids = [p.id for p in query.all()]

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

    return render_template("products/detail.html", product=product, nav=nav, ativos=ativos)


@bp.route("/produtos/<int:id>/uso")
def usage(id):
    qtd = OrderItem.query.filter_by(product_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/produtos/<int:id>/excluir", methods=["POST"])
def delete(id):
    product = Product.query.get_or_404(id)

    usage = OrderItem.query.filter_by(product_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{product.nome}' — está em {usage} pedido(s). "
            f"Remova o produto dos pedidos primeiro.",
            "danger",
        )
        return redirect(url_for("products.edit", id=id))

    ProductIngredient.query.filter_by(product_id=id).delete()
    db.session.delete(product)
    db.session.commit()
    flash("Produto excluído!", "success")
    return redirect(url_for("products.list"))


@bp.route("/produtos/<int:id>/toggle")
def toggle(id):
    product = Product.query.get_or_404(id)
    product.ativo = not product.ativo
    db.session.commit()
    flash("Produto atualizado!", "success")
    return redirect(url_for("products.edit", id=id))


def _remove_imagem(product):
    if not product.imagem:
        return
    upload_dir = os.path.join(
        current_app.root_path, "static", "uploads"
    )
    filepath = os.path.join(upload_dir, product.imagem)
    if os.path.exists(filepath):
        os.remove(filepath)
    product.imagem = None


def _handle_imagem(request, product):
    if "imagem" not in request.files:
        return
    file = request.files["imagem"]
    if not file or file.filename == "":
        return
    if not allowed_file(file.filename):
        flash("Formato de imagem não permitido. Use PNG, JPG, GIF ou WebP.", "warning")
        return

    if product.imagem:
        _remove_imagem(product)

    upload_dir = os.path.join(
        current_app.root_path, "static", "uploads"
    )
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    nome_arquivo = f"prod_{product.id}_{secure_filename(file.filename)}"
    filepath = os.path.join(upload_dir, nome_arquivo)
    file.save(filepath)
    product.imagem = nome_arquivo


UNIDADES_RECEITA = ["kg", "g", "L", "ml", "un", "cx", "pacote", "colher", "colher_sopa", "xicara", "pitada", "litro"]


def _parse_ingredients(request):
    result = []
    ing_ids = request.form.getlist("ingredient_id")
    quantities = request.form.getlist("quantidade")
    unidades = request.form.getlist("unidade")
    for ing_id, qtd, un in zip(ing_ids, quantities, unidades):
        if ing_id and qtd and un:
            result.append((int(ing_id), float(qtd), un))
    return result
