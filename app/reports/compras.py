from ajsystem.defs.report import *

# Nome do DOCUMENTO por status. `STATUS_COMPRA` (app/extends/constants.py) é o
# rótulo do ESTADO — é o que a coluna `status` mostra ("Cancelado"); aqui é o
# nome do documento impresso ("Cancelamento de Pedido"). São vocabulários de
# propósito diferente, por isso ficam separados e não se misturam.
DOCUMENTO = {0: 'Orçamento', 1: 'Pedido',
             6: 'Cancelamento de Pedido', 9: 'Devolução de Pedido'}

# Frase de abertura do documento, escolhida pelo status. `{observacao}` entra no
# MEIO dela, e é por isso que isto é catálogo de `status` e não um texto fixo:
# o report resolve por `{status}` e o catálogo devolve a frase já montada. O
# `wrap` abaixo existe porque a frase do cancelamento é mais larga que a área
# útil da página (206mm contra 190mm) — sem ele, a ponta saía da folha.
FRASE = {
    0: 'Solicitamos o orçamento referente aos seguintes itens:',
    1: 'Conforme negociação anterior, solicitamos o fornecimento dos seguintes itens:',
    6: 'Conforme conversado anteriormente, por motivo de {observacao|(não informado)}, solicitamos o cancelamento do pedido com os seguintes itens:',
    9: 'Conforme conversado anteriormente, por motivo de {observacao|(não informado)}, estamos devolvendo os seguintes itens:',
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
                      {'TEXT': {'text': 'Total: {total:brl|R$ 0,00}', 'align': 'R', 'font_size': 11, 'font_style': 'B'}}],
        },
    },
}
