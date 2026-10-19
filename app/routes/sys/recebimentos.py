from app.models.movimento import Movimento
from ajsystem.defs.constants import TODAY
from app.extends.constants import ENTRADA
from app.routes.sys.movtos import (
    post_save_movto_link, _pre_get_movto, excluir_movto, _validar_origem_exclusiva,
)


def excluir(id):
    return excluir_movto(id, 'recebimentos.list', 'Recebimento')

PREVISOES = {
    'source': 'Previsao',
    'join': 'transacao',
    'columns': ['id', 'documento', 'vencimento', 'previsto',
                'realizado', 'variacao', 'saldo'],
    'when': ["transacao.tipo = 'R'", 'saldo > 0'],
    'params': {'conta_id': 'transacao.conta_id'},
    'order': ['vencimento'],
}

Schema = {
    'Movimento': {
        'data': {'default': TODAY},
        'tipo': {'default': ENTRADA},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}},
                     'carry': 'conta_id'},
        'valor': {'carry': 'valor'},
        'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES'},
                        'on_set': {'replaces': {'valor': 'saldo'}}},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                   'when': 'tipo = 1 AND ativa = true AND pai_id IS NOT NULL'}},
    },
}

Page = {
    'label': 'Recebimento',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Movimento',
            'filter': {'fixed': {'tipo': ENTRADA}},
            'hidden': ['tipo', 'pedido_id', 'compra_id'],
            'card': ['historico'],
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Movimento',
            'positions': {'hidden': ['tipo']},
            'delete': False,
            'pre_get': _pre_get_movto,
            'pre_save': _validar_origem_exclusiva,
            'post_save': post_save_movto_link,
            'buttons': [
                # O que sobra de `delete` aqui é o que difere do tipo: destino
                # (a rota de exclusão é a única que estorna o lançamento) e a
                # mensagem de confirmação. Rótulo, ícone, cor e posição saem do
                # catálogo — por isso `resolve_buttons` declara o tipo.
                {'delete': {'url': 'recebimentos.excluir', 'method': 'POST',
                            'confirm_msg': 'Excluir este lançamento?', 'position': 'bottom_left'}},
            ],
        },
    },
}
