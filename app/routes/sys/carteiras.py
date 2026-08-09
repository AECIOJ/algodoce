from flask import flash

from app.ajsystem.form import em_uso
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.quote import Quote


Entity = {
    'Carteira': {
        'id':                 {'type': 'ID', 'width': 6},
        'nome':               {'type': 'TEXT', 'width': 50, 'transform': 'title'},
        'uso':                {'type': 'LIST', 'width': 10, 'list': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}},
        'gerar':              {'type': 'LIST', 'width': 10, 'list': {0: 'Movimento', 1: 'Previsão'}},
        'prazo_recebimento':  {'type': 'INT', 'width': 5},
        'taxa_recebimento':   {'type': 'NUM', 'width': 8},
    },
}

List = {
    'fields': 'Carteira',
    'ordering': ['nome'],
}


def _carteira_pre_save(instance, request, is_new):
    if not is_new and em_uso(instance, [Compra, Order, Quote]):
        flash("Carteira já utilizada — não pode ser alterada. Crie uma nova.", "warning")
        return False
    return True


def _carteira_pre_get(mod, id):
    if id is None:
        return {}
    carteira = Carteira.query.get(id)
    if not carteira:
        return {}
    in_uso = em_uso(carteira, [Compra, Order, Quote])
    return {'em_uso': in_uso, 'ro': True} if in_uso else {'em_uso': False}


Form = {
    'fields': 'Carteira',
    'form_tail': 'sys_carteira/_form_tail.html',
    'page_scripts': 'sys_carteira/_page_scripts.html',
    'pre_save': _carteira_pre_save,
    'delete': {
        'when': [Compra, Order, Quote],
        'msg_ok': 'Carteira excluída!',
        'msg_no': 'Carteira em uso — não pode ser excluída.',
    },
    'pre_get': _carteira_pre_get,
}