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
from app.models.unit_conversion import UnitConversion
from app.constants import PRODUCAO_ETAPAS, UND_INSUMO
from app.models.category import Category
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_boolean_filter, apply_select_filter, build_fk_options
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form
from app.fields import FIELD_ID, FIELD_NOME, FIELD_ATIVO, FIELD_DESCRICAO, FIELD_PRECO, FIELD_QUANTIDADE


PRODUCTS_FIELDS = {
    'id':         {**FIELD_ID, 'width': 7},
    'nome':       {**FIELD_NOME, 'width': 20},
    'imagem':     {'width': 15, 'filter': False},
    'categoria':  {'query': 'category', 'card_path': 'category.nome', 'filter_path': 'category.nome'},
    'qtd_minima': {'label': 'Qtd. Mín.', 'width': 8, 'input': 'number'},
    'preco':      {'label': 'Preço', 'width': 10, 'input': 'number', 'align': 'right', 'currency': 'brl'},
    'ativo':      {**FIELD_ATIVO},
}

products_list = {'fields': PRODUCTS_FIELDS, 'edit_endpoint': 'products.form'}


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


def _remove_imagem(product):
    if not product.imagem:
        return
    upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
    filepath = os.path.join(upload_dir, product.imagem)
    if os.path.exists(filepath):
        os.remove(filepath)
    product.imagem = None


def _handle_imagem(request, product):
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    if "imagem" not in request.files:
        return
    file = request.files["imagem"]
    if not file or file.filename == "":
        return
    ext = file.filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        flash("Formato de imagem não permitido. Use PNG, JPG, GIF ou WebP.", "warning")
        return
    if product.imagem:
        _remove_imagem(product)
    upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    nome_arquivo = f"prod_{product.id}_{secure_filename(file.filename)}"
    file.save(os.path.join(upload_dir, nome_arquivo))
    product.imagem = nome_arquivo


def _products_pre_save(instance, request, is_new):
    if request.form.get("remover_imagem"):
        _remove_imagem(instance)
    else:
        temp_imagem = request.form.get("temp_imagem")
        if temp_imagem and temp_imagem.startswith("temp_"):
            upload_dir = os.path.join(current_app.root_path, "..", "dados", "uploads")
            old = os.path.join(upload_dir, temp_imagem)
            ext = temp_imagem.rsplit(".", 1)[1].lower()
            new_name = f"prod_{instance.id}_crop.{ext}"
            new_path = os.path.join(upload_dir, new_name)
            if os.path.exists(old):
                os.rename(old, new_path)
                instance.imagem = new_name
        _handle_imagem(request, instance)

    ProductIngredient.query.filter_by(product_id=instance.id).delete()
    db.session.flush()
    for ing_id, qtd, un, eta in _parse_insumos(request):
        db.session.add(ProductIngredient(
            product_id=instance.id, ingredient_id=ing_id,
            quantidade=qtd, unidade=un, etapa_id=eta,
        ))


products_form = {'model': Product, 'redirect': 'products.list', 'fields': {'model': Product, 'fields': {
        'nome':        {**FIELD_NOME},
        'descricao':   FIELD_DESCRICAO,
        'preco':       {**FIELD_PRECO, 'required': True},
        'qtd_minima':  {'label': 'Qtd. Mínima', 'input': 'number', 'attrs': {'min': 0, 'step': 1}},
        'category_id': {'label': 'Categoria', 'input': 'select', 'query': 'category'},
    }}, 'sessions': {
        'Insumos': {'model': ProductIngredient, 'type': 'table', 'template': 'sys_products/_ingredients.html', 'fields': {
            'ingredient_id': {'label': 'Insumo', 'input': 'select'},
            'quantidade':    {**FIELD_QUANTIDADE, 'label': 'Qtd'},
            'unidade':       {'label': 'Und', 'input': 'select', 'options': {u: u for u in UND_INSUMO}},
            'etapa_id':      { 'input': 'select'},
        }},
    }, 'entity_label': 'Produto', 'new_title': 'Novo Produto',
    'body_template': 'sys_products/_form_body.html',
    'footer_left': 'sys_products/_footer_left.html',
    'page_scripts': 'sys_products/_page_scripts.html',
    'buttons': [
        {'label': 'Ativar', 'endpoint': 'products.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': False}},
        {'label': 'Desativar', 'endpoint': 'products.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': True}},
    ],
    'pre_save': _products_pre_save, 'flash_ok': 'Produto cadastrado!', 'flash_update': 'Produto atualizado!'}


bp = Blueprint("products", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/produtos")
def list():
    _list = List(**products_list)
    filter_config = build_filter_config(PRODUCTS_FIELDS)
    active = resolve_filters(filter_config, request.args)
    products = Product.query.order_by(Product.nome).all()
    linhas = products[:]
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_select_filter(linhas, 'categoria', active.get('categoria'), build_fk_options(Category), filter_path='category.nome')
    linhas = apply_number_filter(linhas, 'qtd_minima', active.get('qtd_minima'))
    linhas = apply_number_filter(linhas, 'preco', active.get('preco'))
    linhas = apply_boolean_filter(linhas, 'ativo', active.get('ativo'))
    products = linhas
    ctx = build_field_context(PRODUCTS_FIELDS)
    return render_template("sys_products/list.html", products=products, PRODUCTS_LIST=_list, ctx=ctx, active_filters=active, FILTERS=filter_config)


@bp.route("/produtos/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/produtos/<int:id>/editar", methods=["GET", "POST"])
def form(id=None):
    ingredients_list = Ingredient.query.order_by(Ingredient.nome).all()
    categorias = Category.query.order_by(Category.ordem, Category.nome).all()
    etapas = [type('_Etapa', (), {'id': i, 'nome': n})() for i, n in PRODUCAO_ETAPAS.items()]
    return handle_form(products_form, id, extra_ctx={
        'ingredients': ingredients_list,
        'categorias': categorias,
        'etapas': etapas,
        'UND_INSUMO': UND_INSUMO,
    })


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
        return redirect(url_for("products.form", id=id))
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
    return redirect(url_for("products.form", id=id))


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
    with open(os.path.join(upload_dir, nome), "wb") as f:
        f.write(raw)
    product.imagem = nome
    db.session.commit()
    return jsonify(success=True, filename=nome, url=url_for("uploads.uploaded_file", filename=nome))
