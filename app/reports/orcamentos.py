from ajsystem.defs.report import *


ORCAMENTO = {
    'label': 'Orçamento',
    'header': [
        LOGO('L', 4),
        PROW(0),
        TABS(1, 30),
        TITLES([
            'Orçamento #{id}',
            ('Status: {status}', {'when': 'status > 0'}),
        ]),
        FIELDS(('cliente_nome', {'tab': 1}),
               ('data_pedido', {'tab': 2, 'rows_after': 1}),
               ('cliente_telefone', {'tab': 1}),
               ('validade_data', {'tab': 2})),
        LF(2)
    ],
    'body': {
        'table': {
            'columns': {
                'produto_id':     {'width': 44},
                'qtd':            {'width': 10},
                'preco':          {'label': 'Preço (R$)', 'width': 26},
                'OrcamentoItem.valor': {'label': 'Valor (R$)', 'width': 26, 'agg': 'sum'},
            },
            'totals': {'label': 'Total', 'align': 'R', 'span': 3},
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
