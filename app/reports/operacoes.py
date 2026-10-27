"""Duas peças que não podem se separar: a **fonte** (`QPLANO`, um `QuerySpec`
compartilhado pela listagem e pelo report) e o **papel** (`PLANO`, que só
aponta para ela).

O código hierárquico é montado no próprio `select` (`over` + `calc`), então a
grade e o PDF bebem a mesma string — sem N+1 e sem duas implementações do mesmo
índice.
"""
from ajsystem.defs.report import *
from ajsystem.defs.constants import START, FINISH, NEVER, ROW, INLINE
QPLANO = {
    # Ordem de dependência (leitura top-down): a grade declara a sua ordem
    # na rota; avaliação independe daqui (overs antes dos calcs, ver qrun).
    'select': [
        'id',
        'tipo',
        {'grupo': {
            'func': 'denserank',
            'over': {'partition': ['tipo'], 'order': [{'coalesce': ['pai_id', 'id']}]},
            'label': 'Grupo', 'width': 8,
        }},
        {'index': {
            'func': 'rownumber',
            'over': {'partition': ['tipo', 'pai_id'], 'order': ['ordem', 'id']},
            'label': 'Seq', 'width': 8,
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
            'groups': {
                'tipo': {'text': '{tipo:d}. {tipo}', 'on_start': {'lf': -1}},
                'grupo': {'text': '{tipo:d}.{grupo:02d} {nome}', 'on_start': {}},
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
    'footer': True,
}
