from app.report import Report


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


COMPRA_REPORT = Report(
    label='Compra',
    header={
        'layout': 'logo_left',
        'title': _report_title,
        'fields': [
            {'function': _fornecedor_nome, 'label': 'Fornecedor'},
            {'field': 'data', 'label': 'Data', 'align': 'right', 'format': 'date'},
        ],
    },
    before_table=_report_before,
    table={
        'columns': {
            'insumo.nome':   {'label': 'Insumo', 'width': 50},
            'quantidade':    {'label': 'Qtd.', 'width': 15, 'align': 'center'},
            'preco':         {'label': 'Preço', 'width': 20, 'align': 'right', 'format': 'brl'},
            'valor':         {'label': 'Valor', 'width': 20, 'align': 'right', 'format': 'brl',
                              'function': lambda i: (i.preco or 0) * i.quantidade,
                              'aggregate': 'sum'},
        },
        'footer': True,
        'footer_label': 'Total',
    },
    after_table=_report_after,
)
