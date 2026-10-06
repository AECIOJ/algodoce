from ajsystem.defs.report import *


def _cliente_nome(order):
    return order.conta.nome if order.conta else '-'


def _cliente_telefone(order):
    return order.conta.telefone if order.conta else ''


PEDIDO = {
    'label': 'Pedido',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+40),
        TITLE('Pedido Nº {id}', {'location': [PCOL, 0]}),
        POS(PCOL,2),
        FIELDS(cliente_nome={'function': _cliente_nome, 'label': 'Cliente', 'tab': 1},
               pedido_em={'tab': 2, 'rows_after': 1},
               cliente_telefone={'function': _cliente_telefone, 'label': 'Telefone', 'tab': 1},
               data_previsao_entrega={'tab': 2}),
        LF(2)
    ],
    'body': {
        'table': {
            'columns': {
                'produto.nome':   {'label': 'Produto', 'width': 50},
                'qtd':            {'width': 10},
                'preco':          {'width': 20},
                'PedidoItem.valor': {'width': 20, 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'extend': [([1, 3], 'Acréscimo', {'align': 'R', 'when': 'acrescimo'}),
                       (4, '{acrescimo}', {'when': 'acrescimo'}),
                       ([1, 3], 'Desconto', {'align': 'R', 'when': 'desconto'}),
                       (4, '{desconto}', {'when': 'desconto'}),
                       ([1, 3], 'Total', {'align': 'R', 'font_style': 'B'}),
                       (4, '{total}', {'font_style': 'B'})],
            'after': [
                IND(LTB,RTB),
                FIELDS('Evento', tipo={'label': 'Evento', 'when': 'evento.tipo'},
                             tema={'when': 'evento.tema'},
                             local={'when': 'evento.local'},
                             convidados={'when': 'evento.convidados'},
                             cerimonial={'when': 'evento.cerimonial'},
                             obs={'when': 'evento.obs', 'rows_after': 1}),
                      {'TEXT': {'text': 'Data: {evento.data:%d/%m/%Y} {evento.hora:%H:%M}', 'when': 'evento.data'}},
                      {'TEXT': {'text': 'Forminhas: {forminhas} | Forma de Pagamento: {conta.nome|-}'}}],
        },
    },
}
