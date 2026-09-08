Entity = {
    'Produto': {
        'nome':        {'type': 'TEXT'},
        'descricao':   {'type': 'MEMO', 'rows': 4},
        'imagem':      {'type': 'IMAGE'},
        'qtd_minima':  {'type': 'INT'},
        'categoria_id': {'type': 'FK'},
    },
    'Categoria': {'nome': {'type': 'TEXT'}},
}

Page = {
    'type': 'showcase',
    'route': 'vitrine',
    'max_width': 100,
    'props': {
        'fields': 'Produto',
        'filter': 'Categoria',
        'layout': 'carousel',
        'show': {
            'nome':       'title',
            'imagem':     'left',
            'descricao':  'right',
            'qtd_minima': 'qty',
        },
        'client_fields': ['nome', 'telefone'],
        'badge_id': 'bnOrcamentoBadge',
    },
}
