import os
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, current_app, jsonify
)
from flask_login import login_required
from app.extensions import db
from app.models.product import Product
from app.models.ingredient import Ingredient
from app.models.product_ingredient import ProductIngredient
from app.constants import PRODUCAO_ETAPAS
from app.models.category import Category
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem
from app.fields import Field, build_field_context


PRODUCTS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='imagem', label='Imagem', width=15, filter=False),
    Field(name='nome', label='Nome', width=20),
    Field(name='categoria', label='Categoria', width=15, query='category'),
    Field(name='qtd_minima', label='Qtd. Mín.', width=8, input='number', aggregate='sum'),
    Field(name='preco', label='Preço', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='ativo', label='Status', input='boolean'),
]

bp = Blueprint("products", __name__)


@bp.before_request
@login_required
def protect():
    pass

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/produtos")
def list():
    products = Product.query.order_by(Product.nome).all()
    ctx = build_field_context(PRODUCTS_FIELDS)
    return render_template("products/list.html", products=products, fields=PRODUCTS_FIELDS, ctx=ctx)


@bp.route("/produtos/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        product = Product(
            nome=request.form["nome"],
            descricao=request.form.get("descricao", ""),
            preco=request.form["preco"],
            qtd_minima=request.form.get("qtd_minima", 0, type=int) or 0,
            category_id=request.form.get("category_id", type=int) or None,
        )
        db.session.add(product)
        db.session.flush()

        temp_imagem = request.form.get("temp_imagem")
        if temp_imagem and temp_imagem.startswith("temp_"):
            upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
            old = os.path.join(upload_dir, temp_imagem)
            ext = temp_imagem.rsplit(".", 1)[1].lower()
            new_name = f"prod_{product.id}_crop.{ext}"
            new_path = os.path.join(upload_dir, new_name)
            if os.path.exists(old):
                os.rename(old, new_path)
                product.imagem = new_name

        _handle_imagem(request, product)

        insumos = _parse_insumos(request)
        for ing_id, qtd, un, eta in insumos:
            pi = ProductIngredient(
                product_id=product.id,
                ingredient_id=ing_id,
                quantidade=qtd,
                unidade=un,
                etapa_id=eta,
            )
            db.session.add(pi)

        db.session.commit()
        flash("Produto cadastrado!", "success")
        return redirect(url_for("products.list"))

    categorias = Category.query.order_by(Category.ordem, Category.nome).all()
    ingredients = Ingredient.query.order_by(Ingredient.nome).all()
    etapas = [type('_Etapa', (), {'id': i, 'nome': n})() for i, n in PRODUCAO_ETAPAS.items()]
    return render_template("products/form.html", ingredients=ingredients, categorias=categorias, etapas=etapas)


@bp.route("/produtos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    product = Product.query.get(id)
    if not product:
        flash("Código inexistente", "warning")
        return redirect(url_for("products.list"))
    if request.method == "POST":
        product.nome = request.form["nome"]
        product.descricao = request.form.get("descricao", "")
        product.preco = request.form["preco"]
        product.qtd_minima = request.form.get("qtd_minima", 0, type=int) or 0
        product.category_id = request.form.get("category_id", type=int) or None

        if request.form.get("remover_imagem"):
            _remove_imagem(product)
        else:
            _handle_imagem(request, product)

        ProductIngredient.query.filter_by(product_id=product.id).delete()
        db.session.flush()

        insumos = _parse_insumos(request)
        for ing_id, qtd, un, eta in insumos:
            pi = ProductIngredient(
                product_id=product.id,
                ingredient_id=ing_id,
                quantidade=qtd,
                unidade=un,
                etapa_id=eta,
            )
            db.session.add(pi)

        db.session.commit()
        flash("Produto atualizado!", "success")
        return redirect(url_for("products.list"))

    categorias = Category.query.order_by(Category.ordem, Category.nome).all()
    ingredients = Ingredient.query.order_by(Ingredient.nome).all()
    etapas = [type('_Etapa', (), {'id': i, 'nome': n})() for i, n in PRODUCAO_ETAPAS.items()]

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
        "products/form.html", product=product, ingredients=ingredients, categorias=categorias, etapas=etapas, nav=nav
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


@bp.route("/produtos/<int:id>/uso")
def usage(id):
    qtd = (
        OrderItem.query.filter_by(product_id=id).count()
        + QuoteItem.query.filter_by(product_id=id).count()
    )
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/produtos/<int:id>/excluir", methods=["POST"])
def delete(id):
    product = Product.query.get_or_404(id)

    usage = (
        OrderItem.query.filter_by(product_id=id).count()
        + QuoteItem.query.filter_by(product_id=id).count()
    )
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


@bp.route("/produtos/upload-temp", methods=["POST"])
def upload_temp():
    data = request.get_json(silent=True)
    if not data or "imagem" not in data:
        return jsonify(error="Nenhuma imagem"), 400

    import base64, re, uuid
    match = re.match(r"data:image/(\w+);base64,(.+)", data["imagem"])
    if not match:
        return jsonify(error="Formato inválido"), 400
    ext = match.group(1)
    if ext not in ("png", "jpeg", "gif", "webp"):
        return jsonify(error="Formato não permitido"), 400

    raw = base64.b64decode(match.group(2))
    upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    nome = f"temp_{uuid.uuid4().hex}.{ext}"
    path = os.path.join(upload_dir, nome)
    with open(path, "wb") as f:
        f.write(raw)
    return jsonify(success=True, filename=nome)


@bp.route("/produtos/<int:id>/upload-foto", methods=["POST"])
def upload_foto(id):
    product = Product.query.get_or_404(id)
    data = request.get_json(silent=True)
    if not data or "imagem" not in data:
        return jsonify(error="Nenhuma imagem enviada"), 400

    import base64, re
    match = re.match(r"data:image/(\w+);base64,(.+)", data["imagem"])
    if not match:
        return jsonify(error="Formato inválido"), 400

    ext = match.group(1)
    if ext not in ("png", "jpeg", "gif", "webp"):
        return jsonify(error="Formato não permitido"), 400

    raw = base64.b64decode(match.group(2))

    if product.imagem:
        _remove_imagem(product)

    upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    nome = f"prod_{id}_crop.{ext}"
    path = os.path.join(upload_dir, nome)
    with open(path, "wb") as f:
        f.write(raw)
    product.imagem = nome
    db.session.commit()

    return jsonify(success=True, filename=nome, url=url_for("uploads.uploaded_file", filename=nome))


def _remove_imagem(product):
    if not product.imagem:
        return
    upload_dir = os.path.join(
        current_app.root_path, "..", "dados", "uploads"
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
        current_app.root_path, "..", "dados", "uploads"
    )
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    nome_arquivo = f"prod_{product.id}_{secure_filename(file.filename)}"
    filepath = os.path.join(upload_dir, nome_arquivo)
    file.save(filepath)
    product.imagem = nome_arquivo


UNIDADES_RECEITA = ["kg", "g", "L", "ml", "un", "cx", "pacote", "colher", "colher_sopa", "xicara", "pitada", "litro"]


def _parse_insumos(request):
    result = []
    ing_ids = request.form.getlist("ingredient_id")
    quantities = request.form.getlist("quantidade")
    unidades = request.form.getlist("unidade")
    etapas = request.form.getlist("etapa_id")
    for ing_id, qtd, un, eta in zip(ing_ids, quantities, unidades, etapas):
        if ing_id and qtd and un:
            result.append((int(ing_id), float(qtd), un, int(eta) if eta else None))
    return result
