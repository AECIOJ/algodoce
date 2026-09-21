from app.models.conta import Conta
from app.models.pedido import Pedido

Schema = {
    'Conta': {
        'email': {'pos_list': 2},
        'endereco': {'pos_list': 2},
    },
}

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
            'max_width': 90,
            'fields': 'Conta',
            'sessions': {
                'Pedidos': {
                    'query': {
                        'columns': {'Pedido': ['id','pedido_em','total','status'] },
                        'groups': 'status',
                        'order': 'pedido_em desc',
                        'totals': ['total',],
                    },
                },
            },
            'buttons': ['on_off'],
        },
    },
}
