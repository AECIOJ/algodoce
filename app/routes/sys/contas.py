from app.models.conta import Conta
from app.models.pedido import Pedido

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
            'card': ['email', 'endereco'],
            'order': ['nome'],
        },
        'form': {
            'max_width': 90,
            'fields': 'Conta',
            'positions': {'bar': ['ativo']},
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
        },
    },
}
