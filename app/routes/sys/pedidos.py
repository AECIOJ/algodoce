from ajsystem.core.do_report import print_report
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order import Entity as OrderEntity
from app.models.order_item import Entity as OrderItemEntity
from app.reports.pedidos import PEDIDO

# Entity aninhada para o motor de relatórios (`_module_entity`).
Entity = {
    'Order': OrderEntity,
    'OrderItem': OrderItemEntity,
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
    'Order': {
        'client_id': {'label': 'Cliente',
                      'lookup': {'display': 'nome', 'fields': ['nome', 'telefone'],
                                 'when': {'ativo': True, 'tipo': [0, 1]}}},
        'carteira_id': {'label': 'Pagamento',
                        'lookup': {'display': 'nome'}},
        'status': {'pos_form': 4},
        'total': {'editor': 'eTotal'},
    },
    'OrderItem': {
        'product_id': {
            'lookup': {
                'replaces': {
                    'quantidade': 'qtd_minima',
                    'preco_unitario': 'preco_unitario',
                },
            },
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
            'columns': 'Order',
            'order': ['data_entrega'],
        },
        'form': {
            'max_width': 130,
            'fields': 'Order',
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
                        'columns': ['OrderItem'],
                        'totals': ['quantidade', {'valor': 'eTotal'}],
                    },
                },
                'Evento': {
                    'fields': ['Event'],
                },
            },
        },
    },
}