from ajsystem.defs.report import *


PEDIDO = {
    'label': 'Pedido',
    'header': [
        LOGO('L', 4),
        PROW(0),
        TITLES([
            'Pedido Nº {id}',
            ('Status: {status}', {'when': 'status > 0'}),
        ]),
        LF(1),
        CPI(15),
        TABS(1, 40),
        TABS('{conta_id}', '{pedido_em}'),
        TABS('{Conta.telefone}', '{data_previsao_entrega}'),
        LF(3)
    ],
    'body': {
        'table': {
            'columns': {
                'produto_id':     { 'width':40},
                'qtd':            {},
                'preco':          {'label': 'Preço (R$)'},
                'PedidoItem.valor': {'label': 'Valor (R$)', 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'extend': [([1, 3], 'Acréscimo', {'align': 'R', 'when': 'acrescimo'}),
                       (4, '{acrescimo}', {'when': 'acrescimo'}),
                       ([1, 3], 'Desconto', {'align': 'R', 'when': 'desconto'}),
                       (4, '{desconto}', {'when': 'desconto'}),
                       ([1, 3], 'Total', {'align': 'R', 'style': 'B'}),
                       (4, '{total}', {'style': 'B'})],
            'after': [
                    IND(LTB,RTB),
                    FIELDS(
                        'forminhas','carteira_id',
                        ('Evento.tipo', {'label': 'Evento', 'when': 'evento.tipo'}),
                        ('Evento.tema', {'when': 'evento.tema'}),
                        ('Evento.data', {'when': 'evento.data'}),
                        ('Evento.hora', {'when': 'evento.data'}),
                        ('Evento.local', {'when': 'evento.local'}),
                        ('Evento.convidados', {'when': 'evento.convidados'}),
                        ('Evento.cerimonial', {'when': 'evento.cerimonial'}),
                        ('Evento.obs', {'when': 'evento.obs'})
                    ),
            ]
        },
    },
    'footer': True,

}
