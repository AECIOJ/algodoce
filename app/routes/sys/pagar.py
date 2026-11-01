from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.routes.sys.transacoes import (
    pre_get_transacao, post_save_transacao)
from ajsystem.defs.constants import NOT_EMPTY, OR
from app.extends.masks import MVALOR

Schema = {
    'Transacao': {
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}},
                     'carry': 'conta_id'},
        'operacao_id': {'lookup': {'when': 'tipo = 2 AND pai_id IS NOT NULL'}},
        'tipo': {'default': 'P'},
    },
    'Previsao': {
        'id': {'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'saldo': {},
    },
}

Page = {
    'label': 'Conta a Pagar',
    'type': 'crud',
    'props': {
        # JS dos botões de previsão (Gerar/Zerar) — resolvido pelo motor em
        # `static/js/previsoes.js`, com `?v=` automático pelo mtime.
        'scripts': ['previsoes'],
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Previsao',
            'line': ['id', {'Transação': 'Transacao.id'}, {'Fornecedor': 'Transacao.conta_id'},
                     'Transacao.fatura', 'documento', 'vencimento', 'recurso_id',
                     'previsto', 'realizado', 'variacao', 'saldo', {'Compra': 'Transacao.compra_id'}],
            'hidden': ['transacao_id', 'tipo', 'cancelado'],
            'order': ['vencimento', 'id'],
            'edit_id': 'transacao.id',
        },
        'filter': {
            'fixed': {'tipo': 'P'},
            'types': {'checklist': 'status'},
            'default': OR(
                {'data': {'preset': 'mes_ano'}},
                {'vencimento': {'preset': 'mes_ano'}},
                {'saldo': {'mode': 'maior_que', 'val1': 0}},
            ),
        },
        'form': {
            'max_width':110,
            'fields': 'Transacao',
            # Onde cada campo vai na tela e sob que condição (5.5). `tipo` é
            # filtro fixo (`filter.fixed`): some do painel e vira WHERE,
            # então precisa estar em `hidden` para não virar campo do form.
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
                    'fields': ['valor', 'previsto', 'realizado', 'variacao', 'saldo',
                               'ratear', 'prazo', 'recurso_id'],
                    'table': {
                        'columns': ['Previsao'],
                        'totals': ['previsto', 'realizado', 'variacao', 'saldo'],
                    },
                    'positions': {'hidden': ['saldo'], 'body': ['id']},
                    # `gerar_previsoes` e `zerar_previsoes` são tipos do app
                    # (app/extends/buttons.py): aqui fica só o que depende do form — a
                    # ação JS, a posição e os campos que habilitam.
                    #
                    # Antes cada botão trazia `cls` com a classe toda escrita à
                    # mão, o que bypassava o catálogo inteiro. As classes
                    # marcador (`btn-gerar-previsoes`) não eram lidas por nada
                    # e foram junto.
                    'buttons': [
                        {'gerar_previsoes': {
                            'position': 'top_left',
                            'action': 'gerarPrevisoes',
                            'enabled': ['conta_id', 'operacao_id', 'prazo',
                                        'recurso_id', 'valor', 'ratear']}},
                        {'zerar_previsoes': {
                            'position': 'top_left',
                            'action': 'zerarPrevisoes',
                            'enabled': {'fields': ['realizado', 'variacao'],
                                        'mode': 'all_zero'}}},
                    ],
                },
            },
        },
    },
}
