from ajsystem.defs.constants import NOT_EMPTY, OR, TODAY
from app.extends.masks import MVALOR
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.reports.receber import RECEBER
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Cliente',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'when': 'tipo = 1 AND pai_id IS NOT NULL'}},
        'tipo': {'default': 'R'},
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
        'master': 'Transacao',
        'scripts': ['previsoes'],
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
            'Relatórios': {'type': 'Report'},
        },
        'list': {
            'columns': 'Previsao',
            'hidden': ['Transacao.id','tipo', 'cancelado','compra_id'],
            'order': ['vencimento', 'id'],
            'prio': [
                (2, 'conta_id'),
                (3, 'fatura'),
                (-3, 'pedido_id'),
                (-2, 'status'),
                (-1, 'transacao_id'),
            ],
        },
        'filter': {
            'fixed': {'tipo': 'R'},
            'types': {'checklist': 'status'},
            'default': OR(
                {'data': {'preset': 'mes_ano'}},
                {'vencimento': {'preset': 'mes_ano'}},
                {'saldo': {'mode': 'maior_que', 'val1': 0}},
            ),
        },
        'report':{
            'Saldo de Contas a Receber': {
                'filter':{'conta_id':'=',
                          'vencimento': ('<', TODAY() ) },
                'report': RECEBER
            },
            'Previsão de Contas a Receber': {
                'filter':{'conta_id':'=','vencimento':'<>'},
                # 'report': RECEBER
            },
            'Extrato de Cliente': {
                'filter':{'conta_id':'=','data':'<>'},
                #'report': RECEBER
            },
        },
        'form': {
            'max_width':110,
            'fields': 'Transacao',
            # `tipo` é filtro fixo (`filter.fixed`): some do painel e vira
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
