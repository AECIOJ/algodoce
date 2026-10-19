from app.models.produto import Produto
from app.models.produto_insumo import ProdutoInsumo
from app.models.pedido_item import PedidoItem
from app.models.orcamento_item import OrcamentoItem

Schema = {
    'Produto': { 
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
            'card': ['descricao'],
            'order': ['nome'],
        },
        'form': {
            'max_width': 115,
            'fields': 'Produto',
            'positions': {'hidden': ['qtd_receita'], 'bar': ['ativo']},
            # `qtd_receita` é campo do pai usado só na sessão de insumos: fica
            # oculto no cabeçalho e citado explicitamente na sessão, que é
            # autoritativa (5.5.2).
            'delete': {
                'when': [PedidoItem, OrcamentoItem],
                'msg_ok': 'Produto excluído!',
                'msg_no': 'Não é possível excluir. Produto já em uso.',
            },
            'sessions': {
                'Insumos': {
                    'fields': ['qtd_receita'],
                    'table': {
                        'columns': ['ProdutoInsumo'],
                    }
                },
            },
        },
    },
}