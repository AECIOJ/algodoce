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
        'historico': {'pos_list': 2},
        'cancelado': {'pos_list': 0},
        'total_previsto': {'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)',
                                    'diff': 'Aviso de Inconsistência: Total previsto difere da soma das previsões atuais.'},
                           'readonly': True, 'pos_list': 0},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta conta difere do status calculado.'},
                   'pos_form': 4, 'pos_filter': 3, 'pos_list': 0,
                   'tag': {'colors': {0: 'warning', 1: 'warning', 2: 'info', 8: 'error', 9: 'success'}}},
        'valor': {'carry': 'valor'},
        'tipo': {'pos_filter': 9, 'default': 'P'},
        'pedido_id': {'pos_form': 2, 'readonly': True, 'pos_list': 0, 'tag': {'link': 'pedidos.form', 'color': 'info'}},
        'compra_id': {'pos_form': 2, 'readonly': True, 'pos_list': 0, 'tag': {'link': 'compras.form', 'color': 'info'}},
    },
    'Previsao': {
        'carteira_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'saldo': {'pos_form': 0},
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
