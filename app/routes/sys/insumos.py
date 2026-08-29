from app.models.ingredient import Ingredient
from app.models.unit_conversion import UnitConversion
from app.models.product_ingredient import ProductIngredient
from app.models.producao_insumo import ProducaoInsumo
from app.models.compra_item import CompraItem

Schema = {}

Page = {
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Ingredient',
            'order': ['nome'],
        },
        'form': {
            'fields': 'Ingredient',
            'delete': {ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion},
            'sessions': {
                'Conversões': {
                    'table': {
                        'columns': ['UnitConversion'],
                    }
                },
                'Produtos': {
                    'query': {
                        'columns': ['ProductIngredient'],
                    }
                },
            },
        },
    },
}
