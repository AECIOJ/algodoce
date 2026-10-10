from ajsystem.defs.report import *


PEDIDO = {
    'label': 'Pedido',
    'header': [
        LOGO('L', 4),
        PROW(0),
        CPI(12),
        TABS(1, 30),
        TITLES([
            'Pedido Nº {id}',
            ('Status: {status}', {'when': 'status > 0'}),
        ]),
        FIELDS(('conta_id', {'tab': 1}),
               ('pedido_em', {'tab': 2, 'lf': 1}),
               ('Conta.telefone', {'tab': 1}),
               ('data_previsao_entrega', {'tab': 2})),
        LF(2)
    ],
    'body': {
        'table': {
            'columns': {
                'produto.nome':   {'label': 'Produto', 'width': 50},
                'qtd':            {'width': 10},
                'preco':          {'label': 'Preço (R$)', 'width': 26},
                'PedidoItem.valor': {'label': 'Valor (R$)', 'width': 26, 'agg': 'sum'},
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
}
