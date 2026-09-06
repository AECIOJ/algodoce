from app.models.movimento import Movimento
from app.routes.sys.movto import sync_movto_save, excluir_movto


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
        'tipo': {'pos_filter': 9, 'default': 'S'},
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'label': 'Fornecedor',
                     'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True, 'tipo': [1, 2]}}},
        'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES',
                                'replaces': {'valor': 'saldo'}}},
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
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Movimento',
            'delete': False,
            'post_save': sync_movto_save,
            'buttons': [
                {'label': 'Excluir', 'icon': 'trash', 'color': 'danger', 'outline': False,
                 'endpoint': 'pagamentos.excluir', 'url_var': 'id', 'method': 'POST',
                 'confirm_msg': 'Excluir este lançamento?', 'position': 'footer_left'},
            ],
        },
    },
}
