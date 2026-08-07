from flask import request, redirect, url_for, flash, jsonify
from app.extensions import db
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem
from app.constantes import PRODUCAO_ETAPAS, UND_LIST
from app.ajsystem.form import _delete_uploaded
from app.ajsystem.engine import auto


Entity = {
    'Product': {
        'id':          {'type': 'ID', 'width': 6},
        'nome':        {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'preco':       {'type': 'NUM', 'required': True, 'currency': True},
        'qtd_minima':  {'type': 'INT', 'label': 'Qtd. Mínima', 'attrs': {'min': 0, 'step': 1}},
        'category_id': {'type': 'FK', 'width': 12},
        'ativo':       {'type': 'LOGICO', 'edit': False},
        'imagem':      {'type': 'IMAGE', 'filter': False, 'required': False},
        'descricao':   {'type': 'MEMO', 'rows': 4},
    },
    'ProductIngredient': {
        '__meta__':        {'label': 'Insumos'},
        'product_id':      {'type': 'ID'},
        'ingredient_id':   {'type': 'FK', 'label': 'Insumo', 'required': True},
        'quantidade':      {'type': 'NUM', 'required': True},
        'unidade':         {'type': 'LIST', 'list': UND_LIST, 'required': True},
        'etapa':           {'type': 'LIST', 'list': PRODUCAO_ETAPAS},
    },
}

List = {
    'columns': [
        'Product.id',
        'Product.nome',
        'Product.preco',
        'Product.qtd_minima',
        'Product.imagem',
        'Product.category_id',
        'Product.ativo',
    ],
    'ordering': ['nome'],
}


Form = {
    'fields': 'Product',
    'buttons': ['on_off'],
    'delete': {
        'when': [OrderItem, QuoteItem],
        'msg_ok': 'Produto excluído!',
        'msg_no': 'Não é possível excluir — está em uso.',
    },
    'sessions': {
        'Insumos': {'table': ['ProductIngredient']},
    },
}


@auto.rota("/search")
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


@auto.rota("/<int:id>/uso")
def usage(id):
    qtd = (
        OrderItem.query.filter_by(product_id=id).count()
        + QuoteItem.query.filter_by(product_id=id).count()
    )
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@auto.rota("/<int:id>/excluir", methods=["POST"], endpoint='delete')
def delete(id):
    from app.ajsystem.form import can_delete
    product = Product.query.get_or_404(id)
    if not can_delete(product, [OrderItem, QuoteItem]):
        flash(
            f"Não é possível excluir '{product.nome}' — está em uso.",
            "danger",
        )
        return redirect(url_for("produtos.form", id=id))
    ProductIngredient.query.filter_by(product_id=id).delete()
    _delete_uploaded(product.imagem)
    db.session.delete(product)
    db.session.commit()
    flash("Produto excluído!", "success")
    return redirect(url_for("produtos.list"))
