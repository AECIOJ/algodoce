from ajsystem.defs.constants import POS_EXPLICIT_NOT_EMPTY
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Cliente',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 1 AND pai_id IS NOT NULL'}},
        'historico': {'pos_list': 2},
        'cancelado': {'pos_list': 0, 'pos_form': 5},
        'valor': {'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)',
                           'diff': 'Aviso de Inconsistência: Valor difere da soma das previsões atuais.'},
                  'readonly': True, 'pos_form': 0},
        'prazo': {'calc': {'type': 'call', 'source': 'calc_prazo',
                           'diff': 'Aviso de Inconsistência: Prazo difere do resumo dos vencimentos atuais.'},
                  'readonly': True, 'pos_form': 0},
        'variacao': {'calc': {'type': 'agg', 'source': 'sum(Previsao.variacao)',
                              'diff': 'Aviso de Inconsistência: Variação difere da soma das variações das previsões atuais.'},
                     'readonly': True, 'pos_form': 0},
        'saldo': {'calc': {'type': 'agg', 'source': 'sum(Previsao.saldo)',
                           'diff': 'Aviso de Inconsistência: Saldo difere da soma dos saldos das previsões atuais.'},
                  'readonly': True, 'pos_form': 0},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta conta difere do status calculado.'},
                   'pos_form': 3, 'pos_filter': 3,
                   'tag': {'colors': {0: 'warning', 1: 'warning', 2: 'info', 8: 'error', 9: 'success'}}},
        'tipo': {'pos_filter': 9, 'default': 'R'},
        'pedido_id': {'pos_form': POS_EXPLICIT_NOT_EMPTY, 'readonly': True, 'pos_list': 0, 
                    'tag': {'link': 'pedidos.form', 'color': 'info'}},
        'compra_id': {'pos_form': POS_EXPLICIT_NOT_EMPTY, 'readonly': True, 'pos_list': 0, 
                    'tag': {'link': 'compras.form', 'color': 'info'}},
    },
    'Previsao': {
        'id': {'pos_form': 1, 'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
        'carteira_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'saldo': {'pos_form': 0},
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
            'max_width':110,
            'fields': 'Transacao',
            'pre_get': pre_get_transacao,
            'post_save': post_save_transacao,
            'sessions': {
                'Previsões': {
                    'fields': ['prazo', 'valor', 'variacao', 'saldo'],
                    'table': {
                        'columns': ['Previsao'],
                        'totals': [{'previsto': 'valor'}, 'realizado', 'variacao', 'saldo'],
                    },
                },
            },
        },
    },
}
