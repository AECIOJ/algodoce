from types import SimpleNamespace
from app.report import Report
from app.constants import TIPO_OPERACAO
from app.extensions import db
from app.models.operacao import Operacao
from app.tools import list_table
from sqlalchemy import select


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


def _operacao_data():
    cte = list_table(TIPO_OPERACAO)
    tipos = db.session.execute(select(cte.c)).all()
    secao_map = {s['tipo']: s for s in _build_tree()}

    data = []
    for t in tipos:
        cod, desc = t.codigo, t.descricao
        data.append(SimpleNamespace(
            indice=str(cod), id=None, nome=desc, fator=None, ativa=None
        ))
        secao = secao_map.get(cod)
        if secao:
            for item in secao["flat"]:
                op = item["operacao"]
                data.append(SimpleNamespace(
                    indice=item['indice'], id=op.id, nome=op.nome,
                    fator=op.fator, ativa=op.ativa
                ))
    return data


def _ativa_text(row):
    return 'Sim' if row.ativa else 'Nao'


OPERACAO_REPORT = Report(
    label='Operações',
    ordem='indice',
    data_fn=_operacao_data,
    groups=[
        {
            'position': 'Titulo',
            'format': {'font_style': 'B', 'indent': 2},
        },
        {
            'position': 'Linha',
            'format': {'font_style': 'B', 'indent': 6},
        },
    ],
    header={
        'logo': {'position': 'C'},
        'titulo': {'label': 'Operações'},
    },
    table={
        'lines_after': 1,
        'columns': {
            'indice':         {'label': 'Indice', 'width': 22},
            'id':             {'label': '#', 'width': 12, 'align': 'center'},
            'nome':           {'label': 'Nome', 'width': 80},
            'fator':          {'label': 'Fator', 'width': 14, 'align': 'center'},
            'ativa':          {'label': 'Ativa', 'width': 14, 'align': 'center',
                               'function': _ativa_text},
        },
    },
    footer={'show_user': True, 'show_datetime': True, 'show_page_number': True},
)
