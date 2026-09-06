from datetime import date
from app.models.transferencia import Transferencia
from app.models.movimento import Movimento

Schema = {
    'Transferencia': {},
    'Movimento': {
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True}}},
        'data': {'default': date.today},
        'previsao_id': {'pos_form': 0},
        'operacao_id': {'pos_form': 0},
        'variacao': {'pos_form': 0},
        'sincronizar': {'pos_form': 0},
    },
}

Page = {
    'label': 'Transferência',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Transferencia',
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Transferencia',
            'sessions': {
                'Movimentações': {
                    'table': {
                        'columns': ['Movimento'],
                    },
                },
            },
        },
    },
}
