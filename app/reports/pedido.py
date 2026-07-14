from app.report import Report
from app.constants import FORMINHAS


def _valor_item(item):
    return (item.preco_unitario or 0) * item.quantidade


def _cliente_nome(order):
    return order.conta.nome if order.conta else '-'


def _cliente_telefone(order):
    return order.conta.telefone if order.conta else ''


def _forminhas_carteira(order):
    f = FORMINHAS.get(order.forminhas, '-')
    c = order.carteira.nome if order.carteira else '-'
    return f"Forminhas: {f} | Forma de Pagamento: {c}"


ORDER_REPORT = Report(
    label='Pedido',
    header={
        'layout': 'logo_left',
        'title': 'Pedido #{id}',
        'fields': [
            {'function': _cliente_nome, 'label': 'Cliente'},
            {'field': 'data_pedido', 'label': 'Data', 'align': 'right', 'format': 'datetime'},
            {'function': _cliente_telefone, 'label': 'Telefone'},
            {'field': 'data_previsao_entrega', 'label': 'Previsão', 'align': 'right', 'format': 'datetime'},
        ],
    },
    table={
        'columns': {
            'product.nome':   {'label': 'Produto', 'width': 50},
            'quantidade':     {'label': 'Qtd.', 'width': 10, 'align': 'center'},
            'preco_unitario': {'label': 'Preço', 'width': 20, 'align': 'right', 'format': 'brl'},
            'valor':          {'label': 'Valor', 'width': 20, 'align': 'right', 'format': 'brl',
                               'function': _valor_item, 'aggregate': 'sum'},
        },
        'footer': True,
        'footer_label': 'Total',
        'after': _forminhas_carteira,
    },
)
