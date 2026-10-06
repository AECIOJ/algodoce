"""Plano de Contas: QPLANO (fonte, compartilhável list/report) + PLANO (papel).

Código em 3 segmentos: tipo (direto), grupo (denserank por família), index
(rownumber entre irmãos). O 'indice' montado nasce no select via calc —
grade e PDF bebem a mesma string, sem N+1.
"""
from ajsystem.defs.report import *
QPLANO = {
    # Ordem de dependência (leitura top-down): a grade declara a sua ordem
    # na rota; avaliação independe daqui (overs antes dos calcs, ver qrun).
    'select': [
        'id',
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
        {'indice': {
            'calc': '{tipo:d}.{grupo:02d}{?pai_id:.{index:03d}}',
            'label': 'Código', 'width': 14,
        }},
        'nome',
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
    'header': [
        LOGO(),
        TITLE(),
    ],
    'body': {
        'source': QPLANO,
        'table': {
            'rows_after': 1,
            'groups': {
                'tipo': {'action': 1, 'print': 3, 'text': '{tipo:d}. {tipo}'},
                'grupo': {'action': 1, 'print': 2, 'text': '{tipo:d}.{grupo:02d} {nome}'},
            },
            'columns': [
                'indice',
                'nome',
                {'id': {'width': 6, 'label': '#'}},
                {'fator': {'width': 10}},
                {'ativa': {'width': 8}},
            ],
        },
    },
    'footer': {'show_user': True, 'show_datetime': True, 'show_page_number': True},
}
