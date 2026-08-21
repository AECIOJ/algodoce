from app.constantes import TIPO_OPERACAO
from app.models.operacao import Operacao


def _build_tree():
    todas = Operacao.query.order_by(Operacao.ordem, Operacao.id).all()
    filhos = {}
    for r in todas:
        filhos.setdefault(r.pai_id, []).append(r)

    def _build(pid, tipo):
        items = []
        for r in sorted(filhos.get(pid, []), key=lambda x: (x.ordem, x.id)):
            if r.tipo != tipo:
                continue
            item = {"operacao": r, "filhos": _build(r.id, tipo)}
            items.append(item)
        return items

    def _assign(tree, prefix):
        items = []
        for i, node in enumerate(tree, 1):
            idx = f"{prefix}.{i}" if prefix else str(i)
            node["indice"] = idx
            items.append(node)
            items.extend(_assign(node["filhos"], idx))
        return items

    secoes = []
    for tipo_num in sorted(TIPO_OPERACAO):
        tree = _build(None, tipo_num)
        if tree:
            flat = _assign(tree, str(tipo_num))
            secoes.append({"tipo": tipo_num, "label": TIPO_OPERACAO[tipo_num], "tree": tree, "flat": flat})
    return secoes


PLANO = {
    'label': 'Plano de Contas',
    'ordem': 'indice',
    'header': {
        'logo': {'position': 'C'},
        'titulo': {'label': 'Plano de Contas'},
    },
    'groups': {
        'tipo': {'pos': 'titulo', 'code': True},   # '1. Receitas'
        'left(indice,2)': {'pos': 'linha'},        # subgrupo: raiz + filhos
    },
    'table': {
        'lines_after': 1,
        'columns': {
            'indice': {'width': 10},   # label 'Índice' da Entity
            'id':      {'width': 6},   # label '#'
            'nome':    {},             # label 'Nome'
            'fator':   {'width': 10},  # INT → center
            'ativa':   {'width': 8},   # BOOL → Sim/Não
        },
    },
    'footer': {'show_user': True, 'show_datetime': True, 'show_page_number': True},
}
