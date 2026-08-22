PLANO = {
    'label': 'Plano de Contas',
    'header': {
        'logo': {'position': 'C'},
        'title': {'label': 'Plano de Contas'},
    },
    'groups': [
        {'indice': {'left': 1, 'pos': 2, 'transform':'upper',
                    'text': '{indice}. {tipo}'}},        # título: '1. Receitas'
        {'indice': {'left': 2, 'pos': 1, 'skip': True,
                    'text': '{indice} {nome}'}},         # bloco: '1.01 Vendas'
    ],
    'table': {
        'columns': {
            'indice': {'width': 12},   # label 'Índice' da Entity
            'id':      {'width': 6, 'label': '#'},
            'nome':    {},             # label 'Nome'
            'fator':   {'width': 10},  # INT → center
            'ativa':   {'width': 8},   # BOOL → Sim/Não
        },
    },
    'footer': {'show_user': True, 'show_datetime': True, 'show_page_number': True},
}
