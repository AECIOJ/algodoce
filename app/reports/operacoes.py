PLANO = {
    'label': 'Plano de Contas',
    'header': {
        'logo': {'position': 'C'},
        'title': {'label': 'Plano de Contas'},
    },
    'body': {
        'source': {'entity': 'Operacao', 'order': 'indice'},
        'table': {
            'columns': {
                'indice': {'width': 12},   # label 'Índice' da Entity
                'nome':   {},              # label 'Nome'
                'id':     {'width': 6, 'label': '#'},
                'fator':  {'width': 10},   # INT → center
                'ativa':  {'width': 8},    # BOOL → Sim/Não
            },
            'hierarchy': [
                {'indice': {'left': 1, 'pos': 2, 'transform': 'upper',
                            'text': '{indice}. {tipo}'}},       # título: '1. RECEITAS'
                {'indice': {'left': 2, 'pos': 1,
                            'text': '{indice} {nome}'}},        # linha: '1.1 RECEITAS COM VENDAS'
            ],
        },
    },
    'footer': {'show_user': True, 'show_datetime': True, 'show_page_number': True},
}
