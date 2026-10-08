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
# `Observações`, no fim do documento. O `wrap` abaixo continua necessário
# porque a frase aponta para longe e ainda passa da área útil.
FRASE = {
    0: 'Solicitamos o orçamento referente aos seguintes itens:',
    1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
    6: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, solicitamos o cancelamento do pedido com os seguintes itens:',
    9: 'Conforme conversado anteriormente, por motivo abaixo discriminado em observações, estamos devolvendo os seguintes itens:',
}


def _report_title(compra):
    return f'{DOCUMENTO.get(compra.status, "Compra")} #{compra.id}'


def _report_before(compra):
    # Faturado (2) e Recebido (8) não são pedidos: não há frase a pedir, e o
    # bloco inteiro some. A lista de status mora no catálogo acima — não num
    # tuple repetido, que é o que divergia quando entrava status novo.
    if compra.status not in FRASE:
        return []
    return [
        {'text': ''},
        {'text': '{fornecedor.nome|-}', 'font_size': 12, 'font_style': 'B', 'align': 'C'},
        {'text': ''},
        {'text': '{status}', 'labels': {'status': FRASE}, 'wrap': True},
    ]


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
        'before': _report_before,
        'table': {
            'columns': {
                'insumo.nome':   {'label': 'Insumo', 'width': 50},
                'qtd':           {'width': 10},
                'preco':         {'width': 20},
                'CompraItem.valor': {'width': 20, 'agg': 'sum'},
            },
            'totals': {'label': 'Subtotal', 'align': 'R', 'span': 3},
            'after': [{'TEXT': {'text': ''}},
                      {'TEXT': {'text': '_' * 40, 'align': 'C'}},
                      {'TEXT': {'text': 'Acréscimo: {acrescimo:brl}', 'align': 'R', 'when': 'acrescimo'}},
                      {'TEXT': {'text': 'Desconto: {desconto:brl}', 'align': 'R', 'when': 'desconto', 'rows_after': 1}},
                      {'TEXT': {'text': 'Total: {total:brl|R$ 0,00}', 'align': 'R', 'font_size': 11, 'font_style': 'B'}},
                      # O motivo do cancelamento/devolução, aqui no fim em vez de
                      # no meio da frase de abertura. `body.after` serviria, mas
                      # ele renderiza ANTES deste bloco (ver pdf.py): o lugar do
                      # "depois da tabela" de verdade é `table.after`.
                      #
                      # `rows_before` e não `LF(2)`: o respiro tem de sumir
                      # junto com o bloco, e `LF` não tem `when` — o rows_before
                      # do item é descartado junto com o item quando o `when`
                      # falha. `wrap` porque a observação é livre e pode ser
                      # bem maior que a página.
                      {'TEXT': {'text': 'Observações', 'when': 'observacao',
                                'rows_before': 2, 'font_style': 'B'}},
                      {'TEXT': {'text': '{observacao}', 'when': 'observacao', 'wrap': True}}],
        },
    },
}
