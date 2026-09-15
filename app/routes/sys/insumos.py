from app.models.insumo import Insumo
from app.models.insumo_conversao import InsumoConversao
from app.models.produto_insumo import ProdutoInsumo
from app.models.producao_insumo import ProducaoInsumo
from app.models.compra_item import CompraItem

Schema = {
    'InsumoConversao': {
        'und': {'on_set': {'replaces': {'fator': 0}}},
    },
}

Page = {
    'label': 'Insumo',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Insumo',
            'order': ['nome'],
        },
        'form': {
            'max_width': 70,
            'fields': 'Insumo',
            'delete': {ProdutoInsumo, ProducaoInsumo, CompraItem, InsumoConversao},
            'sessions': {
                'Conversões': {
                    'table': {
                        'columns': ['InsumoConversao'],
                    }
                },
                'Produtos': {
                    'query': {
                        'columns': ['ProdutoInsumo'],
                    }
                },
            },
        },
    },
}
