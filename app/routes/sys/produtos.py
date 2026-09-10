from app.models.produto import Produto
from app.models.produto_insumo import ProdutoInsumo
from app.models.pedido_item import PedidoItem
from app.models.orcamento_item import OrcamentoItem

Schema = {
    'Produto': { 
        'qtd_receita': {'pos_form' : 0 },
        },
}

Page = {
    'label': 'Produto',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Produto',
            'order': ['nome'],
        },
        'form': {
            'max_width': 115,
            'fields': 'Produto',
            'buttons': ['on_off'],
            'delete': {
                'when': [PedidoItem, OrcamentoItem],
                'msg_ok': 'Produto excluído!',
                'msg_no': 'Não é possível excluir. Produto já em uso.',
            },
            'sessions': {
                'Insumos': {
                    'fields': ['qtd_receita'],
                    'query': {
                        'columns': ['ProdutoInsumo'],
                    }
                },
            },
        },
    },
}