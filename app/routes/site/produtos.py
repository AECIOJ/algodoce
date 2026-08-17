Entity = {
    'Product': {
        'nome':        {'type': 'TEXT'},
        'descricao':   {'type': 'MEMO', 'rows': 4},
        'imagem':      {'type': 'IMAGE'},
        'qtd_minima':  {'type': 'INT'},
        'category_id': {'type': 'FK', 'query': 'category'},
    },
    'Category': {'nome': {'type': 'TEXT'}},
}

Page = {
    'type': 'showcase',
    'route': 'vitrine',
    'max_width': 100,
    'props': {
        'fields': 'Product',
        'filter': 'Category',
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
