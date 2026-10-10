from ajsystem.defs.report import *

PREAMBULO = {
    0: 'Solicitamos o orçamento referente aos seguintes itens:',
    1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
    6: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, solicitamos o cancelamento do pedido com os seguintes itens:',
    9: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, estamos devolvendo os seguintes itens:',
}


LARGURA = 84


COMPRA = {
    'label': 'Compra',
    'header': [
        LOGO('L', 3),
        PROW(0),
        TABS(5, 40),
        TITLES([
            ('Orçamento #{id}', {'when': 'status == 0'}),
            ('{status == 1 ? Pedido : COMPRA} #{id}', {'when': 'status != 0'}),
            ('Status: {status}', {'when': 'status > 1'}),
        ]),
        TABS('{fornecedor_id}', '{data}'),
        LF(2)
    ],
    'body': {
        'before': [
            MEMO('status', LARGURA, {'recuo':4, 'options': PREAMBULO, 'label': '',
                                     'when': {'status': PREAMBULO}}),
        ],
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo'},
                'qtd':           {},
                'preco':         {'label': 'Preço (R$)'},
                'CompraItem.valor': {'label': 'Valor (R$)', 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'extend': [([1, 3], 'Acréscimo', {'align': 'R', 'when': 'acrescimo'}),
                       (4, '{acrescimo}', {'when': 'acrescimo'}),
                       ([1, 3], 'Desconto', {'align': 'R', 'when': 'desconto'}),
                       (4, '{desconto}', {'when': 'desconto'}),
                       LINE(),
                       ([1, 3], 'Total', {'align': 'R', 'style': 'B', 'when': 'acrescimo or desconto'}),
                       (4, '{total}', {'style': 'B', 'when': 'acrescimo or desconto'})],
            'after': [
                MEMO('observacao', LARGURA, {'label': 'Obs.:', 'lf': -1,
                                             'when': 'observacao'}),
            ],
        },
    },
}
