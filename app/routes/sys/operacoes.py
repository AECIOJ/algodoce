from ajsystem.core.extensions import db
from ajsystem.core.utils import CONNECTORS
from app.models.operacao import Operacao
from app.reports import PLANO


# `filter_field: 'tipo'` imprime o relatório da seleção de filtro corrente (o
# shape de listagem), não o documento — e nesse caso o `guard` não se aplica,
# que é o que a factory `BTN_PRINT` já fazia.
Buttons = {
    'imprimir_plano': {'type': 'print', 'report': PLANO, 'filter_field': 'tipo',
                       'label': 'Plano'},
}

Schema = {
    'Operacao': {
        'indice': {'pos_list': 1, 'pos_filter': 0, 'pos_form': 0},
    }
}


def _transformar_nome(nome, pai_id):
    if not pai_id:
        return nome.strip().upper()
    words = nome.strip().split()
    resultado = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONNECTORS:
            resultado.append(w.lower())
        else:
            resultado.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(resultado)


def _pre_save(instance, request, is_new):
    if instance.fator is None:
        instance.fator = 1
    pai_id = request.form.get("pai_id", type=int) or None
    instance.nome = _transformar_nome(request.form.get("nome", ""), pai_id)
    if is_new or (pai_id is not None and pai_id != instance.pai_id):
        max_ordem = db.session.query(db.func.max(Operacao.ordem)).filter(
            Operacao.pai_id.is_(None)
        ).scalar()
        instance.ordem = (max_ordem or 0) + 1
    instance.pai_id = pai_id


Page = {
    'label': 'Operação',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Operacao',
            'order': ['ordem', 'nome'],
            'buttons': ['imprimir_plano'],
        },
        'form': {
            'max_width': 80,
            'fields': 'Operacao',
            'pre_save': _pre_save,
            'delete': {
                'when': [Operacao],
                'msg_ok': 'Operação excluída!',
                'msg_no': 'Não é possível excluir — existem operações vinculadas.',
            },
            'buttons': [{'on_off': {'field': 'ativa'}}],
        },
    },
}
