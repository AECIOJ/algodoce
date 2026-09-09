def _fornecedor_nome(compra):
    return compra.fornecedor.nome if compra and compra.fornecedor else '-'


def _responsavel_atual(compra):
    for h in compra.historicos or []:
        if h.status == compra.status and h.responsavel:
            return h.responsavel
    return ''


def _motivo_atual(compra):
    for h in compra.historicos or []:
        if h.status == compra.status and h.motivo:
            return h.motivo
    return ''


def _report_title(compra):
    t = {0: 'Orçamento', 1: 'Pedido', 6: 'Cancelamento de Pedido', 9: 'Devolução de Pedido'}
    return f'{t.get(compra.status, "Compra")} #{compra.id}'


def _report_before(compra):
    if compra.status not in (0, 1, 6, 9):
        return []
    txt = {
        0: 'Solicitamos o orçamento referente aos seguintes itens:',
        1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
        6: f'Conforme conversado anteriormente, por motivo de {_motivo_atual(compra) or "(não informado)"}, solicitamos o cancelamento do pedido com os seguintes itens:',
        9: f'Conforme conversado anteriormente, por motivo de {_motivo_atual(compra) or "(não informado)"}, estamos devolvendo os seguintes itens:',
    }.get(compra.status)
    return [
        {'text': ''},
        {'text': _fornecedor_nome, 'font_size': 12, 'font_style': 'B', 'align': 'C'},
        {'text': ''},
        {'text': txt},
    ]


def _report_after(compra):
    return [
        {'text': ''},
        {'text': '_' * 40, 'align': 'C'},
        {'text': _responsavel_atual, 'align': 'C'},
    ]


COMPRA = {
    'label': 'Compra',
    'print_fragment_template': 'components/print_overlay.html',
    'header': {
        'layout': 'logo_left',
        'title': _report_title,
        'fields': [
            {'function': _fornecedor_nome, 'label': 'Fornecedor'},
            {'field': 'data', 'label': 'Data', 'align': 'right', 'format': 'date'},
        ],
    },
    'body': {
        'before': _report_before,
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo', 'width': 50},
                'qtd':         {'label': 'Qtd.', 'width': 10, 'align': 'center',
                                  'format': None},   # NUM sem currency: sem formato (heurística NUM→brl do motor)
                'preco':         {'label': 'Preço', 'width': 20, 'align': 'right'},
                'CompraItem.valor': {'label': 'Valor', 'width': 20, 'align': 'right',
                                     'function': lambda i: (i.preco or 0) * i.qtd,
                                     'agg': 'sum'},   # 'valor' existe em Compra e CompraItem: forma pontilhada desambigua
            },
            'footer': True,
            'footer_label': 'Total',
        },
        'after': _report_after,
    },
}
