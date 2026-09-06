from app.models.carteira import Carteira
from app.models.compra import Compra
from app.models.pedido import Pedido
from app.models.previsao import Previsao
from app.models.orcamento import Orcamento

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
                'when': [Compra, Pedido, Orcamento, Previsao],
                'msg_ok': 'Carteira excluída!',
                'msg_no': 'Carteira em uso — não pode ser excluída.',
            },
        },
    },
}
