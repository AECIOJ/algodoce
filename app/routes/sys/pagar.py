from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)
from ajsystem.defs.constants import TODAY

Schema = {
    'Transacao': {
        'data': {'default': TODAY},
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 2 AND pai_id IS NOT NULL'}},
        'historico': {'pos_list': 2},
        'cancelado': {'pos_list': 0, 'pos_form': 5},
        'valor': {'readonly': False, 'pos_form': 0, 'carry': 'valor'},
        'previsto': {'type': 'NUM', 'label': 'Previsto', 'currency': 1, 'readonly': True,
                     'memory': True, 'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)'}},
        'realizado': {'type': 'NUM', 'label': 'Realizado', 'currency': 1, 'readonly': True,
                      'memory': True, 'calc': {'type': 'agg', 'source': 'sum(Previsao.realizado)'}},
        'ratear': {'type': 'NUM', 'label': 'Ratear', 'currency': 1, 'memory': True},
        'prazo': {'readonly': False, 'pos_form': 0},
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
        'tipo': {'pos_filter': 9, 'default': 'P'},
        'compra_id': {'pos_list': 1},
        'recurso_id': {'pos_list': 1,'type': 'FK', 'label': 'Recurso', 'memory': True,
                       'lookup': {'model': 'Recurso', 'display': 'nome', 'fields': ['nome']}},
    },
    'Previsao': {
        'id': {'pos_form': 1, 'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
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
            'master': 'Previsao',
            'order': ['vencimento'],
            'card': 'Transacao',
        },
        'form': {
            'max_width':110,
            'fields': 'Transacao',
            'pre_get': pre_get_transacao,
            'post_save': post_save_transacao,
            'sessions': {
                'Previsões': {
                    'fields': ['valor', 'previsto', 'realizado', 'variacao', 'saldo',
                               'ratear', 'prazo', 'recurso_id'],
                    'table': {
                        'columns': ['Previsao'],
                        'totals': ['previsto', 'realizado', 'variacao', 'saldo'],
                    },
                    'buttons': [
                        {'label': 'Gerar', 'icon': 'arrow-path',
                         'cls': 'btn-gerar-previsoes btn-success btn-sm',
                         'position': 'table_before',
                         'js': 'gerarPrevisoes(this)'},
                        {'label': 'Zerar', 'icon': 'x-circle',
                         'cls': 'btn-zerar-previsoes btn-warning btn-sm',
                         'position': 'table_before',
                         'js': 'zerarPrevisoes(this)'},
                    ],
                },
            },
        },
    },
}
