from datetime import date
from app.models.trf import Trf
from app.models.movto import Movto

Schema = {
    'Trf': {},
    'Movto': {
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
            'columns': 'Trf',
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Trf',
            'sessions': {
                'Movimentações': {
                    'table': {
                        'columns': ['Movto'],
                    },
                },
            },
        },
    },
}
