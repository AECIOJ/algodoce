from ajsystem.defs.report import FIELD, LOGO, PCOL, TABS, TITLE, POS


ORCAMENTO = {
    'label': 'Orçamento',
    'header': [
        LOGO('L', 3),
        TABS(PCOL, PCOL+30),
        TITLE('Orçamento #{id}', {'location': [PCOL, 0]}),
        POS(PCOL,2),
        FIELD('cliente_nome', {'tab': 1}),
        FIELD('data_pedido', {'tab': 2, 'rows_after': 1}),
        FIELD('cliente_telefone', {'tab': 1}),
        FIELD('validade_data', {'tab': 2, 'rows_after': 2}),
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
            'after': [{'TEXT': {'text': 'Evento: {evento.tipo}', 'font_style': 'B', 'when': 'evento.tipo'}},
                      {'TEXT': {'text': 'Tema: {evento.tema}', 'when': 'evento.tema'}},
                      {'TEXT': {'text': 'Data: {evento.data:%d/%m/%Y} {evento.hora:%H:%M}', 'when': 'evento.data'}},
                      {'TEXT': {'text': 'Local: {evento.local}', 'when': 'evento.local'}},
                      {'TEXT': {'text': 'Convidados: {evento.convidados}', 'when': 'evento.convidados'}},
                      {'TEXT': {'text': 'Cerimonial: {evento.cerimonial}', 'when': 'evento.cerimonial'}},
                      {'TEXT': {'text': 'Obs: {evento.obs}', 'when': 'evento.obs'}},
                      {'TEXT': {'text': 'Forminhas: {forminhas} | Forma de Pagamento: {carteira.nome|50% no pedido + 50% na entrega}'}}],
        },
    },
}
