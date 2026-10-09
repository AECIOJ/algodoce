from ajsystem.defs.report import *


ORCAMENTO = {
    'label': 'Orçamento',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+35),
        TITLES([
            ('Orçamento #{id}', {'location': [PCOL, 0]}),
            # Subtítulo sem `location`: ele FLUI logo abaixo do título, que
            # é a mesma medida (o título ocupa a linha inteira). Sem âncora
            # não há linha mágica, e `status > 0` esconde a linha no
            # documento inicial, onde o subtítulo repetiria o título.
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
                'preco':          {'width': 14},
                'OrcamentoItem.valor': {'width': 14, 'agg': 'sum'},
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
