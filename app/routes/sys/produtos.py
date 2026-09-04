from app.models.product import Product
from app.models.product_ingredient import ProductIngredient
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem

Schema = {}

Page = {
    'label': 'Produto',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Product',
            'order': ['nome'],
        },
        'form': {
            'max_width': 115,
            'fields': 'Product',
            'buttons': ['on_off'],
            'delete': {
                'when': [OrderItem, QuoteItem],
                'msg_ok': 'Produto excluído!',
                'msg_no': 'Não é possível excluir. Produto já em uso.',
            },
            'sessions': {
                'Insumos': {
                    'table': {
                        'columns': ['ProductIngredient'],
                    }
                },
            },
        },
    },
}