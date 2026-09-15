from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 2 AND pai_id IS NOT NULL'}},
        'total_previsto': {'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)',
                                    'diff': 'Aviso de Inconsistência: Total previsto difere da soma das previsões atuais.'},
                           'readonly': True},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta conta difere do status calculado.'},
                   'pos_form': 4},
        'valor': {'carry': 'valor'},
        'tipo': {'pos_filter': 9, 'default': 'P'},
        'pedido_id': {'pos_form': 2, 'readonly': True},
        'compra_id': {'pos_form': 2, 'readonly': True},
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
            'pre_get': pre_get_transacao,
            'post_save': post_save_transacao,
            'sessions': {
                'Previsões': {
                    'table': {
                        'columns': ['Previsao'],
                        'totals': [{'previsto': 'total_previsto'}, 'realizado', 'variacao', 'saldo'],
                    },
                },
            },
        },
    },
}
