from app.models.movto import Movto
from app.routes.sys.movto_sync import sync_movto_save, excluir_movto


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
    'Movto': {
        'tipo': {'pos_filter': 9, 'default': 'E'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [0, 1]}}},
        'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES',
                                'replaces': {'valor': 'saldo'}}},
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
            'columns': 'Movto',
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Movto',
            'delete': False,
            'post_save': sync_movto_save,
            'buttons': [
                {'label': 'Excluir', 'icon': 'trash', 'color': 'danger', 'outline': False,
                 'endpoint': 'recebimentos.excluir', 'url_var': 'id', 'method': 'POST',
                 'confirm_msg': 'Excluir este lançamento?', 'position': 'footer_left'},
            ],
        },
    },
}
