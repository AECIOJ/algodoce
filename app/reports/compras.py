from ajsystem.defs.report import *

# Nome do DOCUMENTO por status. `STATUS_COMPRA` (app/extends/constants.py) é o
# rótulo do ESTADO — é o que a coluna `status` mostra ("Cancelado"); aqui é o
# nome do documento impresso ("Cancelamento de Pedido"). São vocabulários de
# propósito diferente, por isso ficam separados e não se misturam.
DOCUMENTO = {0: 'Orçamento', 1: 'Pedido',
             6: 'Cancelamento de Pedido', 9: 'Devolução de Pedido'}

# Frase de abertura do documento, escolhida pelo status — por isso é catálogo de
# `status` e não texto fixo: o report resolve por `{status}` e recebe a frase já
# montada. O MOTIVO não vem aqui dentro: ele é longo demais para a linha (soube
# passar de 250mm com um motivo só), e a frase só aponta para o bloco
# `Observações`, no fim do documento.
#
# Este catálogo é TAMBÉM a lista de status que têm frase — o `when` dos itens
# do preâmbulo é `{'status': FRASE}`. Faturado (2) e Recebido (8) não estão
# aqui, então nome e frase somem, sem um `if status not in (...)` em Python
# para divergir do texto.
FRASE = {
    0: 'Solicitamos o orçamento referente aos seguintes itens:',
    1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
    6: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, solicitamos o cancelamento do pedido com os seguintes itens:',
    9: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, estamos devolvendo os seguintes itens:',
}

# Largura dos dois blocos de texto do documento, em colunas da grade. Uma
# constante porque o requisito é que tenham o MESMO recuo das margens: com a
# largura no próprio item (e não numa zona `IND`, que vaza para o que vem
# depois e depende de ordem), os dois centralizam com a mesma sobra de cada
# lado.
LARGURA = 84


def _report_title(compra):
    return f'{DOCUMENTO.get(compra.status, "Compra")} #{compra.id}'


COMPRA = {
    'label': 'Compra',
    'header': [
        LOGO('L', 3),
        TABS(PCOL+5, PCOL+40),
        TITLE(_report_title, {'location': [PCOL, 0]}),
        POS(PCOL,2),
        FIELDS(('fornecedor_id', {'tab': 1}),
               ('data', {'tab': 2})),
        LF(2)
    ],
    'body': {
        'before': [
            MEMO('status', LARGURA, {'options': FRASE, 'label': '',
                                     'when': {'status': FRASE}}),
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
                       ([1, 3], 'Total', {'align': 'R', 'font_style': 'B', 'when': 'acrescimo or desconto'}),
                       (4, '{total}', {'font_style': 'B', 'when': 'acrescimo or desconto'})],
            'after': [
                LF(1, {'when': 'observacao'}),
                MEMO('observacao', LARGURA, {'label': 'Obs.:', 'when': 'observacao'}),
            ],
        },
    },
}
