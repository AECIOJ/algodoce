def _fornecedor_nome(compra):
    return compra.fornecedor.nome if compra and compra.fornecedor else '-'


def _report_title(compra):
    t = {0: 'Orçamento', 1: 'Pedido', 6: 'Cancelamento de Pedido', 9: 'Devolução de Pedido'}
    return f'{t.get(compra.status, "Compra")} #{compra.id}'


def _report_before(compra):
    if compra.status not in (0, 1, 6, 9):
        return []
    obs = compra.observacao or '(não informado)'
    txt = {
        0: 'Solicitamos o orçamento referente aos seguintes itens:',
        1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
        6: f'Conforme conversado anteriormente, por motivo de {obs}, solicitamos o cancelamento do pedido com os seguintes itens:',
        9: f'Conforme conversado anteriormente, por motivo de {obs}, estamos devolvendo os seguintes itens:',
    }.get(compra.status)
    return [
        {'text': ''},
        {'text': _fornecedor_nome, 'font_size': 12, 'font_style': 'B', 'align': 'C'},
        {'text': ''},
        {'text': txt},
    ]


def _brl(v):
    if v is None:
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _report_after(compra):
    lines = [
        {'text': ''},
        {'text': '_' * 40, 'align': 'C'},
    ]
    acrescimo = float(compra.acrescimo or 0)
    desconto = float(compra.desconto or 0)
    total = float(compra.total or 0)
    if acrescimo:
        lines.append({'text': f'Acréscimo: {_brl(acrescimo)}', 'align': 'R'})
    if desconto:
        lines.append({'text': f'Desconto: {_brl(desconto)}', 'align': 'R'})
    lines.append({'text': ''})
    lines.append({'text': f'Total: {_brl(total)}', 'align': 'R',
                  'font_size': 11, 'font_style': 'B'})
    return lines


COMPRA = {
    'label': 'Compra',
    'print_fragment_template': 'components/print_overlay.html',
    'header': {
        'layout': 'logo_left',
        'title': _report_title,
        'fields': [
            {'function': _fornecedor_nome, 'label': 'Fornecedor'},
            {'field': 'data', 'align': 'right'},
        ],
    },
    'body': {
        'before': _report_before,
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo', 'width': 50},
                'qtd':           {'width': 10},
                'preco':         {'width': 20},
                'CompraItem.valor': {'width': 20, 'agg': 'sum'},
            },
            'footer': True,
            'footer_label': 'Subtotal',
        },
        'after': _report_after,
    },
}
