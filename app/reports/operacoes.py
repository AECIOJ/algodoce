"""Plano de Contas: QPLANO (fonte, compartilhável list/report) + PLANO (papel).

Código em 3 segmentos: tipo (direto), grupo (denserank por família), index
(rownumber entre irmãos). O 'indice' montado nasce no select via calc —
grade e PDF bebem a mesma string, sem N+1.
"""
QPLANO = {
    'select': [
        'id',
        {'indice': {
            'calc': '{tipo:d}.{grupo:02d}{?pai_id:.{index:03d}}',
            'label': 'Código', 'width': 14,
        }},
        'nome',
        'tipo',
        {'grupo': {
            'func': 'denserank',
            'over': {'partition': ['tipo'], 'order': [{'coalesce': ['pai_id', 'id']}]},
            'pos_list': 0, 'label': 'Grupo', 'width': 8,
        }},
        {'index': {
            'func': 'rownumber',
            'over': {'partition': ['tipo', 'pai_id'], 'order': ['ordem', 'id']},
            'pos_list': 0, 'label': 'Seq', 'width': 8,
        }},
        'fator',
        'ativa',
        'pai_id',
        'ordem',
    ],
    'from': 'Operacao',
    # raiz (pai_id null) antes dos filhos dentro do grupo: null ordena primeiro
    'order': ['tipo', 'grupo', 'pai_id', 'ordem', 'id'],
}

PLANO = {
    'label': 'Plano de Contas',
    'header': {
        'logo': {'position': 'C'},
        'title': {'label': 'Plano de Contas'},
    },
    'body': {
        'source': QPLANO,
        'table': {
            'columns': [
                'indice',
                'nome',
                {'id': {'width': 6, 'label': '#'}},
                {'fator': {'width': 10}},
                {'ativa': {'width': 8}},
            ],
            'groups': [
                {'field': 'tipo', 'print': 1, 'place': 1, 'text': '{tipo:d}. {tipo}'},
                {'field': 'grupo', 'print': 1, 'place': 2, 'text': '{tipo:d}.{grupo:02d} {nome}'},
            ],
        },
    },
    'footer': {'show_user': True, 'show_datetime': True, 'show_page_number': True},
}
