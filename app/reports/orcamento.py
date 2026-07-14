from datetime import timedelta
from app.report import Report
from app.constants import FORMINHAS


def _valor_item(item):
    return (item.preco_unitario or 0) * item.quantidade


def _validade_text(q):
    ref = q.data_renovacao or q.data_pedido
    if not ref:
        return '-'
    venc = (ref + timedelta(days=q.validade or 3)).strftime('%d/%m/%Y')
    txt = f"{venc} ({q.validade} dias)"
    if q.data_renovacao:
        txt = f"Renovado: {q.data_renovacao.strftime('%d/%m/%Y')} | {txt}"
    return txt


def _forminhas_carteira(q):
    f = FORMINHAS.get(q.forminhas, '-')
    c = q.carteira.nome if q.carteira else '50% no pedido + 50% na entrega'
    return f"Forminhas: {f} | Forma de Pagamento: {c}"


ORCAMENTO_REPORT = Report(
    label='Orçamento',
    header={
        'layout': 'logo_left',
        'title': 'Orçamento #{id}',
        'fields': [
            {'field': 'cliente_nome', 'label': 'Cliente'},
            {'field': 'data_pedido', 'label': 'Data', 'align': 'right', 'format': 'datetime'},
            {'field': 'cliente_telefone', 'label': 'Telefone'},
            {'label': 'Validade', 'align': 'right', 'function': _validade_text},
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
