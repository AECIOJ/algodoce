from app.models.movimento import Movimento
from ajsystem.defs.constants import TODAY
from app.extends.constants import SAIDA
from app.routes.sys.movtos import (
    post_save_movto_link, _pre_get_movto, excluir_movto, _validar_origem_exclusiva,
)


def excluir(id):
    return excluir_movto(id, 'pagamentos.list', 'Pagamento')

PREVISOES = {
    'source': 'Previsao',
    'join': 'transacao',
    'columns': ['id', 'documento', 'vencimento', 'previsto',
                'realizado', 'variacao', 'saldo'],
    'when': ["transacao.tipo = 'P'", 'saldo > 0'],
    'params': {'conta_id': 'transacao.conta_id'},
    'order': ['vencimento'],
}

Schema = {
    'Movimento': {
        'data': {'default': TODAY},
        'tipo': {'default': SAIDA},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}},
                     'carry': 'conta_id'},
        'valor': {'carry': 'valor'},
        'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES'},
                        'on_set': {'replaces': {'valor': 'saldo'}}},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                   'when': 'tipo = 2 AND ativa = true AND pai_id IS NOT NULL'}},
    },
}

Page = {
    'label': 'Pagamento',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Movimento',
            'filter': {'fixed': {'tipo': SAIDA}},
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
                {'delete': {'url': 'pagamentos.excluir', 'method': 'POST',
                            'confirm_msg': 'Excluir este lançamento?', 'position': 'bottom_left'}},
            ],
        },
    },
}
