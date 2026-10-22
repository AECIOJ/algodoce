from ajsystem.defs.constants import NOT_EMPTY, OR, TODAY
from app.extends.masks import MVALOR
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)

Schema = {
    'Transacao': {
        'data': {'default': TODAY},
        'conta_id': {'label': 'Cliente',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': 'tipo = 1 AND pai_id IS NOT NULL'}},
        'cancelado': {'label': 'Cancelado em'},
        'valor': {'readonly': False, 'carry': 'valor'},
        'previsto': {'type': 'NUM', 'label': 'Previsto', 'readonly': True,
                     'memory': True, 'mask': MVALOR,
                     'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)'}},
        'realizado': {'type': 'NUM', 'label': 'Realizado', 'readonly': True,
                      'memory': True, 'mask': MVALOR,
                      'calc': {'type': 'agg', 'source': 'sum(Previsao.realizado)'}},
        'ratear': {'type': 'NUM', 'label': 'Ratear', 'memory': True, 'mask': MVALOR},
        'prazo': {'readonly': False},
        'variacao': {'calc': {'type': 'agg', 'source': 'sum(Previsao.variacao)',
                              'diff': 'Aviso de Inconsistência: Variação difere da soma das variações das previsões atuais.'},
                     'readonly': True},
        'saldo': {'calc': {'type': 'agg', 'source': 'sum(Previsao.saldo)',
                           'diff': 'Aviso de Inconsistência: Saldo difere da soma dos saldos das previsões atuais.'},
                  'readonly': True},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta conta difere do status calculado.'},
                   'tag': {'colors': {0: 'warning', 1: 'warning', 2: 'info', 8: 'error', 9: 'success'}}},
        'tipo': {'default': 'R'},
        'recurso_id': {'type': 'FK', 'label': 'Recurso', 'memory': True,
                       'lookup': {'model': 'Recurso', 'display': 'nome', 'fields': ['nome']}},
    },
    'Previsao': {
        'id': {'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'saldo': {},
    },
}

Page = {
    'label': 'Conta a Receber',
    'type': 'crud',
    'props': {
        'scripts': ['previsoes'],
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Transacao',
            'master': 'Previsao',
            'filter': {
                'fixed': {'tipo': 'R'},
                'types': {'checklist': 'status'},
                'default': OR(
                    {'data': {'preset': 'mes_ano'}},
                    {'vencimento': {'preset': 'mes_ano'}},
                    {'saldo': {'mode': 'maior_que', 'val1': 0}},
                ),
            },
            'line': ['pedido_id'],
            'hidden': ['cancelado', 'tipo'],
            'card': 'Transacao',
            'order': ['vencimento', 'id'],
        },
        'form': {
            'max_width':110,
            'fields': 'Transacao',
            # `tipo` é filtro fixo (`list.filter.fixed`): some do painel e vira
            # WHERE, então precisa estar em `hidden` para não virar campo do form.
            'positions': {
                'bar':    ['status'],
                'footer': ['cancelado'],
                'hidden': ['valor', 'prazo', 'variacao', 'saldo', 'tipo',
                           'compra_id', 'pedido_id'],
            },
            'visible': {'pedido_id': NOT_EMPTY,
                        'compra_id': NOT_EMPTY},
            'pre_get': pre_get_transacao,
            'post_save': post_save_transacao,
            'sessions': {
                'Previsões': {
                    'fields': ['valor', 'previsto', 'realizado', 'variacao',
                               'saldo', 'recurso_id', 'prazo', 'ratear'],
                    'table': {'columns': ['Previsao'],
                              'totals': ['previsto', 'realizado', 'variacao', 'saldo']},
                    'positions': {'hidden': ['saldo'], 'body': ['id']},
                    'buttons': [
                        {'gerar_previsoes': {'position': 'top_left',
                            'action': 'gerarPrevisoes',
                            'enabled': ['conta_id', 'operacao_id', 'prazo',
                                        'recurso_id', 'valor', 'ratear']}},
                        {'zerar_previsoes': {'position': 'top_left',
                            'action': 'zerarPrevisoes',
                            'enabled': {'fields': ['realizado', 'variacao'],
                                        'mode': 'all_zero'}}},
                    ],
                },
            },
        },
    },
}
