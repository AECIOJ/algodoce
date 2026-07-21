from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import or_
from app.models.product import Product
from app.models.category import Category

bp = Blueprint("site_vitrine", __name__, url_prefix="/vitrine")


@bp.route("/")
def listar():
    categoria_id = request.args.get("categoria", type=int)
    categorias = Category.query.filter_by(ativo=True).order_by(Category.ordem).all()
    query = Product.query.filter(
        Product.ativo == True,
        or_(
            Product.category_id == None,
            Product.category.has(Category.ativo == True)
        )
    )
    if categoria_id:
        query = query.filter_by(category_id=categoria_id)
    produtos = query.all()
    items = session.get("orcamento_items", [])
    total_itens = len(items)
    itens_ids = [i["product_id"] for i in items]
    itens_qtd = {i["product_id"]: i["quantidade"] for i in items}
    return render_template("site_orcamento/navegador.html",
                           produtos=produtos, categorias=categorias,
                           categoria_id=categoria_id, total_itens=total_itens,
                           itens_ids=itens_ids, itens_qtd=itens_qtd)


@bp.route("/<int:id>/add", methods=["POST"])
def adicionar(id):
    produto = Product.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    quantidade = int(data.get("quantidade", 1))
    observacao = data.get("observacao", "")

    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return jsonify(error="identificar"), 401

    items = session.get("orcamento_items", [])
    found = False
    for i in items:
        if i["product_id"] == id:
            i["quantidade"] += quantidade
            if observacao:
                i["observacao"] = observacao
            found = True
            break
    if not found:
        items.append({
            "product_id": id,
            "quantidade": quantidade,
            "observacao": observacao or None,
        })
    session["orcamento_items"] = items
    total_itens = len(items)
    return jsonify(success=True, total_itens=total_itens)


@bp.route("/<int:id>/update", methods=["POST"])
def atualizar(id):
    data = request.get_json(silent=True) or {}
    quantidade = int(data.get("quantidade", 1))

    items = session.get("orcamento_items", [])
    for i in items:
        if i["product_id"] == id:
            i["quantidade"] = quantidade
            break
    session["orcamento_items"] = items
    total_itens = len(items)
    return jsonify(success=True, total_itens=total_itens)


@bp.route("/<int:id>/remove", methods=["POST"])
def remover(id):
    items = session.get("orcamento_items", [])
    session["orcamento_items"] = [i for i in items if i["product_id"] != id]
    total_itens = len(session["orcamento_items"])
    return jsonify(success=True, total_itens=total_itens)
