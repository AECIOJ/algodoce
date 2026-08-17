from flask import request, redirect, url_for, flash, jsonify
from app.ajsystem.core.extensions import db
from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem
from app.constantes import PRODUCAO_ETAPAS, UND_LIST
from app.ajsystem.core.form import _delete_uploaded, pesquise
from app.ajsystem.core import auto


def insumo_on_set(row):
    """`on_set` do Insumo: quantidade=1 e unidade conforme o insumo."""
    row['quantidade'] = 1
    try:
        iid = int(row.get('ingredient_id'))
    except (TypeError, ValueError):
        return
    und = pesquise('ingredient', iid, 'unidade_medida')
    if und:
        row['unidade'] = und


Entity = {
    'Product': {
        'id':          {'type': 'ID', 'width': 6},
        'nome':        {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'preco':       {'type': 'NUM', 'label': 'Preço', 'required': True, 'currency': True},
        'qtd_minima':  {'type': 'INT', 'label': 'Qtd. Mínima', 'min': 0, 'step': 1},
        'category_id': {'type': 'FK', 'label': 'Categoria', 'width': 12},
        'ativo':       {'type': 'BOOL', },
        'imagem':      {'type': 'IMAGE'},
        'descricao':   {'type': 'MEMO', 'label': 'Descrição', 'rows': 4, 'in_list': 2},
    },
    'ProductIngredient': {
        'product_id':      {'type': 'DK'},
        'ingredient_id':   {'type': 'FK', 'label': 'Insumo', 'required': True, 'on_set': insumo_on_set},
        'quantidade':      {'type': 'NUM', 'required': True},
        'unidade':         {'type': 'LIST', 'list': UND_LIST, 'required': True},
        'etapas':          {'type': 'MULT10', 'list': PRODUCAO_ETAPAS, 'align': 'center'},
    },
}

Page = {
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'fields': 'Product',
            'ordering': ['nome'],
        },
        'form': {
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
        },
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
    from app.ajsystem.core.form import can_delete
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
