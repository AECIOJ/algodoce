from app.models.conta import Conta
from app.models.pedido import Pedido

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
            'max_width': 85,
            'fields': 'Conta',
            'sessions': {
                'Pedidos': {
                    'query': {
                        'columns': ['Pedido'],
                        'groups': 'status',
                        'order': 'data_pedido desc',
                    },
                },
            },
            'buttons': ['on_off'],
        },
    },
}
