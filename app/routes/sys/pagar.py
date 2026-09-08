from app.models.transacao import Transacao
from app.models.previsao import Previsao

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}}},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 2 AND pai_id IS NOT NULL'}},
        'total_previsto': {'input_name': 'ePrevisto'},
        'tipo': {'pos_filter': 9, 'default': 'P'},
    },
    'Previsao': {
        'carteira_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
    },
}

Page = {
    'label': 'Conta a Pagar',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Transacao',
            'order': ['data', 'id'],
            'detail': {'fields': ['documento', 'vencimento', 'previsto',
                                  'realizado', 'variacao', 'saldo'],
                       'data': 'previsoes'},
        },
        'form': {
            'fields': 'Transacao',
            'sessions': {
                'Previsões': {
                    'table': {
                        'columns': ['Previsao'],
                        'totals': [{'previsto': 'ePrevisto'}, 'realizado', 'variacao', 'saldo'],
                    },
                },
            },
        },
    },
}
