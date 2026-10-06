from ajsystem.defs.report import *


ORCAMENTO = {
    'label': 'Orçamento',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+35),
        TITLE('Orçamento #{id}', {'location': [PCOL, 0]}),
        POS(PCOL,2),
        FIELDS(cliente_nome={'tab': 1},
               data_pedido={'tab': 2, 'rows_after': 1},
               cliente_telefone={'tab': 1},
               validade_data={'tab': 2}),
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
                    FIELDS('Evento', tipo={'label': 'Evento', 'when': 'evento.tipo'},
                             tema={'when': 'evento.tema'},
                             local={'when': 'evento.local'},
                             convidados={'when': 'evento.convidados'},
                             cerimonial={'when': 'evento.cerimonial'},
                             obs={'when': 'evento.obs', 'rows_after': 1}),
                      {'TEXT': {'text': 'Data: {evento.data:%d/%m/%Y} {evento.hora:%H:%M}', 'when': 'evento.data'}},
                      {'TEXT': {'text': 'Forminhas: {forminhas}  Forma de Pagamento: {carteira.nome|50% no pedido + 50% na entrega}'}}],
        },
    },
}
