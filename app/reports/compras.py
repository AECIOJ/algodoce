from ajsystem.defs.report import *


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


COMPRA = {
    'label': 'Compra',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+40),
        TITLE(_report_title, {'location': [PCOL, 0]}),
        POS(PCOL,2),
        FIELDS(('fornecedor_id', {'tab': 1}),
               ('data', {'tab': 2})),
        LF(2)
    ],
    'body': {
        'before': _report_before,
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo', 'width': 50},
                'qtd':           {'width': 10},
                'preco':         {'width': 20},
                'CompraItem.valor': {'width': 20, 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'after': [{'TEXT': {'text': ''}},
                      {'TEXT': {'text': '_' * 40, 'align': 'C'}},
                      {'TEXT': {'text': 'Acréscimo: {acrescimo:brl}', 'align': 'R', 'when': 'acrescimo'}},
                      {'TEXT': {'text': 'Desconto: {desconto:brl}', 'align': 'R', 'when': 'desconto', 'rows_after': 1}},
                      {'TEXT': {'text': 'Total: {total:brl|R$ 0,00}', 'align': 'R', 'font_size': 11, 'font_style': 'B'}}],
        },
    },
}
