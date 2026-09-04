from app.models.transacao import Transacao
from app.models.previsao import Previsao

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Cliente',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}}},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 1 AND pai_id IS NOT NULL'}},
        'total_previsto': {'editor': 'ePrevisto'},
        'tipo': {'pos_filter': 9, 'default': 'R'},
    },
    'Previsao': {
        'carteira_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
    },
}

Page = {
    'label': 'Conta a Receber',
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
