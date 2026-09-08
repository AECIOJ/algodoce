from datetime import date
from ajsystem.core.do_report import print_report
from app.models.compra import Compra
from app.models.compra_item import CompraItem
from app.models.compra_historico import CompraHistorico
from app.models.compra import Entity as CompraEntity
from app.models.compra_item import Entity as CompraItemEntity
from app.reports.compras import COMPRA

# Entity aninhada para o motor de relatórios (`_module_entity`).
Entity = {
    'Compra': CompraEntity,
    'CompraItem': CompraItemEntity,
}


def _btn_enviar_action(instance):
    """Botão Enviar do form — pré-controle + impressão da compra.

    Exibição no padrão das listagens (operações/PLANO): o fragmento vai para
    o container exclusivo `#report-content` (via `render`).
    """
    if instance is None or not instance.items:
        return ''
    return print_report(COMPRA, instance)


Schema = {
    'Compra': {
        'data': {'default': date.today},
        'fornecedor_id': {'label': 'Fornecedor',
                          'lookup': {'display': 'nome', 'fields': ['nome', 'telefone'],
                                     'when': {'ativo': True, 'tipo': [1, 2]}}},
        'carteira_id': {'label': 'Pagamento',
                        'lookup': {'display': 'nome'}},
        'status': {'pos_form': 4},
        'valor': {'readonly': True, 'input_name': 'eTotal'},
    },
    'CompraItem': {
        'insumo_id': {
            'lookup': {'display': 'nome', 'fields': ['nome']},
        },
    },
}

Page = {
    'label': 'Compra',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Compra',
            'order': ['data', 'id'],
        },
        'form': {
            'fields': 'Compra',
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success', 'outline': True,
                 'action': _btn_enviar_action, 'render': '#report-content',
                 'position': 'nav_right'},
            ],
            'sessions': {
                'Itens': {
                    'table': {
                        'columns': ['CompraItem'],
                        'totals': ['quantidade', {'valor': 'eTotal'}],
                    },
                },
                'Histórico': {
                    'table': {
                        'columns': ['CompraHistorico'],
                    },
                },
            },
        },
    },
}
