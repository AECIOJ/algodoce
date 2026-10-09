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
        TABS(PCOL+5, PCOL+40),
        POS(PCOL, 0),
        # O título é o NOME do documento e o subtítulo é o ESTADO. Com o
        # subtítulo abaixo, o título não precisa mais carregar cada estado:
        # 'Orçamento' e 'Pedido' dizem o que 0 e 1 já dizem, e de 2 em diante
        # o estado é informação nova. Por isso os dois cortes são complementares
        # (`== 0` / `== 1` contra `> 1`).
        #
        # Só um título desenha em cada documento, e como o `when` é avaliado
        # ANTES do contador da cascata, ele sempre sai como título (16pt).
        # `POS` uma vez no lugar de `location` em cada título: é o mesmo item
        # que este report usava antes, e o título continua na coluna PCOL,
        # linha 0 — que só diverge se o LOGO passar a desenhar.
        TITLES([
            ('Orçamento #{id}', {'when': 'status == 0'}),
            # O ternário escolhe entre Pedido e COMPRA pela MESMA gramática do
            # `when` — um mecanismo só. O guard continua sendo `status != 0`
            # porque o ramo 'COMPRA' cobre tudo que não é 1, status 0 incluído.
            ('{status == 1 ? Pedido : COMPRA} #{id}', {'when': 'status != 0'}),
            ('Status: {status}', {'when': 'status > 1'}),
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
