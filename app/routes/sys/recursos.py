from app.models.recurso import Recurso

Schema = {}

Page = {
    'label': 'Recurso',
    'type': 'crud',
    'props': {
        'master': 'Recurso',
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Recurso',
            'order': ['nome'],
        },
        'form': {
            'max_width': 90,
            'fields': 'Recurso',
        },
    },
}
