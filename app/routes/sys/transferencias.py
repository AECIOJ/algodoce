from datetime import date
from app.models.transferencia import Transferencia
from app.models.movimento import Movimento

Schema = {
    'Transferencia': {
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta transferência difere do status calculado.'},
                   'pos_form': 4, 'pos_filter': 3, 'tag': {'colors': {'Editando': 'neutral', 'Pendente': 'warning', 'Fechada': 'success'}}},
        'historico': {'pos_list': 2},
    },
    'Movimento': {
        'recurso_id': {'lookup': {'display': 'nome', 'fields': ['nome']}},
        'conta_id': {'lookup': {'display': 'nome', 'fields': ['nome'],
                                'when': {'ativo': True}}},
        'data': {'default': date.today},
        'previsao_id': {'pos_form': 0},
        'operacao_id': {'pos_form': 0},
        'variacao': {'pos_form': 0},
        'historico': {'pos_list': 2},
        'pedido_id': {'pos_list': 0, 'tag': {'link': 'pedidos.form', 'color': 'info'}},
        'compra_id': {'pos_list': 0, 'tag': {'link': 'compras.form', 'color': 'info'}},
    },
}

Page = {
    'label': 'Transferência',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Transferencia',
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Transferencia',
            'sessions': {
                'Movimentações': {
                    'table': {
                        'columns': ['Movimento'],
                    },
                },
            },
        },
    },
}
