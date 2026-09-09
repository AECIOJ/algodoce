from ajsystem.core.do_report import print_report
from app.models.pedido import Pedido
from app.models.pedido_item import PedidoItem
from app.models.pedido import Entity as PedidoEntity
from app.models.pedido_item import Entity as PedidoItemEntity
from app.reports.pedidos import PEDIDO

# Entity aninhada para o motor de relatórios (`_module_entity`).
Entity = {
    'Pedido': PedidoEntity,
    'PedidoItem': PedidoItemEntity,
}


def _btn_enviar_action(instance):
    """Botão Enviar do form — pré-controle + impressão do pedido.

    Exibição no padrão das listagens (operações/PLANO): o fragmento vai para
    o container exclusivo `#report-content` (via `render`).
    """
    if instance is None or not instance.items:
        return ''
    return print_report(PEDIDO, instance)


Schema = {
    'Pedido': {
        'conta_id': {'label': 'Cliente',
                      'lookup': {'display': 'nome', 'fields': ['nome', 'telefone'],
                                 'when': {'ativo': True, 'tipo': [0, 1]}}},
        'carteira_id': {'label': 'Pagamento',
                        'lookup': {'display': 'nome'}},
        'status': {'pos_form': 4},
        'total': {'input_name': 'eTotal'},
    },
    'PedidoItem': {
        'produto_id': {
            'on_set': {'replaces': {
                'qtd': 'qtd_minima',
                'preco': 'preco',
            }},
        },
    },
}

Page = {
    'label': 'Pedido',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Pedido',
            'order': ['data_entrega'],
        },
        'form': {
            'max_width': 130,
            'fields': 'Pedido',
            'flash_ok': 'Pedido criado!',
            'flash_update': 'Pedido atualizado!',
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success', 'outline': True,
                 'action': _btn_enviar_action, 'render': '#report-content',
                 'position': 'nav_right'},
            ],
            'sessions': {
                'Itens do Pedido': {
                    'table': {
                        'columns': ['PedidoItem'],
                        'totals': ['qtd', {'valor': 'eTotal'}],
                    },
                },
                'Evento': {
                    'fields': ['Evento'],
                },
            },
        },
    },
}