from ajsystem.defs.report import *

DOCUMENTO = {0: 'Orçamento', 1: 'Pedido',
             6: 'Cancelamento de Pedido', 9: 'Devolução de Pedido'}

PREAMBULO = {
    0: 'Solicitamos o orçamento referente aos seguintes itens:',
    1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
    6: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, solicitamos o cancelamento do pedido com os seguintes itens:',
    9: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, estamos devolvendo os seguintes itens:',
}


LARGURA = 84


def _report_title(compra):
    return f'{DOCUMENTO.get(compra.status, "Compra")} #{compra.id}'


COMPRA = {
    'label': 'Compra',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+40),
        TITLES([
            (_report_title, {'location': [PCOL, 0]}),
            # Subtítulo sem `location`: ele FLUI logo abaixo do título, que
            # é a mesma medida (o título ocupa a linha inteira). Sem âncora
            # não há linha mágica, e `status > 0` esconde a linha no
            # documento inicial, onde o subtítulo repetiria o título.
            ('Status: {status}', {'when': 'status > 0'}),
        ]),
        FIELDS(('fornecedor_id', {'tab': 1}),
               ('data', {'tab': 2})),
        LF(2)
    ],
    'body': {
        'before': [
            MEMO('status', LARGURA, {'recuo':4, 'options': PREAMBULO, 'label': '',
                                     'when': {'status': PREAMBULO}}),
        ],
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo', 'width': 50},
                'qtd':           {'width': 10},
                'preco':         {'width': 20},
                'CompraItem.valor': {'width': 20, 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'extend': [([1, 3], 'Acréscimo', {'align': 'R', 'when': 'acrescimo'}),
                       (4, '{acrescimo}', {'when': 'acrescimo'}),
                       ([1, 3], 'Desconto', {'align': 'R', 'when': 'desconto'}),
                       (4, '{desconto}', {'when': 'desconto'}),
                       LINE(),
                       ([1, 3], 'Total', {'align': 'R', 'font_style': 'B', 'when': 'acrescimo or desconto'}),
                       (4, '{total}', {'font_style': 'B', 'when': 'acrescimo or desconto'})],
            'after': [
                LF(1, {'when': 'observacao'}),
                MEMO('observacao', LARGURA, {'label': 'Obs.:', 'when': 'observacao'}),
            ],
        },
    },
}
