from app.models.movimento import Movimento
from ajsystem.defs.constants import TODAY
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
        'tipo': {'pos_filter': 9, 'default': 'E'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}},
                     'carry': 'conta_id'},
        'valor': {'carry': 'valor'},
        'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES'},
                        'on_set': {'replaces': {'valor': 'saldo'}}},
        'operacao_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                   'when': 'tipo = 1 AND ativa = true AND pai_id IS NOT NULL'}},
        'pedido_id':{'carry':'id', 'pos_list': 0, 'tag': {'link': 'pedidos.form', 'color': 'info'}},
        'compra_id': {'pos_list': 0, 'tag': {'link': 'compras.form', 'color': 'info'}},
        'historico': {'pos_list': 2},
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
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Movimento',
            'delete': False,
            'pre_get': _pre_get_movto,
            'pre_save': _validar_origem_exclusiva,
            'post_save': post_save_movto_link,
            'buttons': [
                {'label': 'Excluir', 'icon': 'trash', 'color': 'danger', 'outline': False,
                 'endpoint': 'recebimentos.excluir', 'url_var': 'id', 'method': 'POST',
                 'confirm_msg': 'Excluir este lançamento?', 'position': 'footer_left'},
            ],
        },
    },
}
