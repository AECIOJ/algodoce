from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.order import Order
from app.models.previsao import Previsao
from app.models.quote import Quote

Schema = {}

Page = {
    'label': 'Carteira',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Carteira',
            'order': ['nome'],
        },
        'form': {
            'max_width': 70,
            'fields': 'Carteira',
            'delete': {
                'when': [Compra, Order, Quote, Previsao],
                'msg_ok': 'Carteira excluída!',
                'msg_no': 'Carteira em uso — não pode ser excluída.',
            },
        },
    },
}
