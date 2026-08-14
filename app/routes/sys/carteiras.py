from flask import flash
from sqlalchemy import select

from app.ajsystem.core.extensions import db
from app.ajsystem.core.form import em_uso
from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.previsao import Previsao
from app.models.quote import Quote


_EM_USO = [Compra, Order, Quote, Previsao]
_NOME_MSG = "Carteira já utilizada — o nome não pode ser alterado."
_USO = {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}
_GERAR = {0: 'Movimento', 1: 'Previsão'}
_PRAZO_HELP = {
    'vazio': 'à vista (vencimento no pedido)',
    'N': 'único vencimento em N dias (ex.: 30)',
    'Nx': 'N parcelas iguais a cada 30 dias (ex.: 3x → 30/60/90)',
    'P/E': 'metade no pedido e metade na entrega',
    'A/B': 'vencimentos em A e B dias (ex.: 0/15)',
}


Entity = {
    'Carteira': {
        'id':                 {'type': 'ID', 'width': 6},
        'nome':               {'type': 'TEXT', 'width': 50, 'transform': 'title'},
        'uso':                {'type': 'LIST', 'width': 10, 'list': _USO},
        'gerar':              {'type': 'LIST', 'width': 10, 'list': _GERAR},
        'prazo_recebimento':  {'type': 'TEXT', 'label': 'Prazo', 'width': 12, 'help': _PRAZO_HELP},
        'taxa_recebimento':   {'type': 'PERCENT', 'label': 'Taxa', 'width': 8},
    },
}

List = {
    'fields': 'Carteira',
    'ordering': ['nome'],
}


def _carteira_pre_save(instance, request, is_new):
    if is_new:
        return True
    with db.session.no_autoflush:
        in_uso = em_uso(instance, _EM_USO)
        atual = db.session.execute(
            select(Carteira.nome).where(Carteira.id == instance.id)
        ).scalar()
    if in_uso and (instance.nome or '').strip().lower() != (atual or '').strip().lower():
        flash(_NOME_MSG, "warning")
        return False
    return True


def _carteira_pre_get(mod, id):
    if id is None:
        return {}
    carteira = Carteira.query.get(id)
    if not carteira:
        return {}
    if em_uso(carteira, _EM_USO):
        return {'em_uso': True, 'ro_fields': {'nome': _NOME_MSG}}
    return {'em_uso': False}


Form = {
    'fields': 'Carteira',
    'pre_save': _carteira_pre_save,
    'delete': {
        'when': _EM_USO,
        'msg_ok': 'Carteira excluída!',
        'msg_no': 'Carteira em uso — não pode ser excluída.',
    },
    'pre_get': _carteira_pre_get,
}