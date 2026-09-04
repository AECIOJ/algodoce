from app.models.client import Conta
from app.models.order import Order

Schema = {}

Page = {
    'label': 'Conta',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Conta',
            'order': ['nome'],
        },
        'form': {
            'max_width': 80,
            'fields': 'Conta',
            'sessions': {
                'Pedidos': {
                    'query': {
                        'columns': ['Order'],
                        'groups': 'status',
                        'order': 'data_pedido desc',
                    },
                },
            },
            'buttons': ['on_off'],
        },
    },
}
