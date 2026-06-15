from flask import Blueprint, render_template, request, jsonify, session
from flask_login import current_user
from app.extensions import db
from app.models.product import Product
from app.models.category import Category
from app.models.client import Client
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from datetime import datetime, timezone

bp = Blueprint("vitrine", __name__, url_prefix="/vitrine")


@bp.route("/")
def listar():
    categoria_id = request.args.get("categoria", type=int)
    categorias = Category.query.filter_by(ativo=True).order_by(Category.ordem).all()
    query = Product.query.filter_by(ativo=True)
    if categoria_id:
        query = query.filter_by(category_id=categoria_id)
    produtos = query.all()
    return render_template("orcamento/navegador.html",
                           produtos=produtos, categorias=categorias, categoria_id=categoria_id)


@bp.route("/<int:id>/add", methods=["POST"])
def adicionar(id):
    produto = Product.query.get_or_404(id)
    data = request.get_json(silent=True) or {}
    quantidade = int(data.get("quantidade", 1))
    observacao = data.get("observacao", "")

    cliente_id = session.get("cliente_id")
    if not cliente_id:
        return jsonify(error="identificar"), 401
    client = Client.query.get(cliente_id)
    if not client:
        return jsonify(error="identificar"), 401

    quote = Quote.query.filter_by(
        cliente_telefone=client.telefone, status=0
    ).order_by(Quote.id.desc()).first()

    if not quote:
        quote = Quote(
            cliente_nome=client.nome,
            cliente_telefone=client.telefone,
            data_pedido=datetime.now(timezone.utc),
        )
        db.session.add(quote)
        db.session.flush()

    item = QuoteItem(
        quote_id=quote.id,
        product_id=produto.id,
        quantidade=quantidade,
        preco_unitario=None,
        observacao=observacao or None,
    )
    db.session.add(item)
    db.session.commit()

    total_itens = QuoteItem.query.filter_by(quote_id=quote.id).count()
    return jsonify(success=True, total_itens=total_itens)
