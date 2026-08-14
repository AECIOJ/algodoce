import os
from io import BytesIO
from flask import request, jsonify, Response, current_app
from app.ajsystem.core.extensions import db
from app.models.operacao import Operacao
from app.constantes import TIPO_OPERACAO, CONECTORES
from app.ajsystem.core import auto


Entity = {
    'Operacao': {
        'id':     {'type': 'ID', 'width': 6},
        'indice': {'label': 'Índice', 'width': 6, 'filter': False, 'in_form': False},
        'nome':   {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':   {'type': 'LIST', 'width': 12, 'list': TIPO_OPERACAO},
        'fator':  {'type': 'INT', 'width': 8},
        'pai_id': {'type': 'FK', 'label': 'Superior', 'query': 'operacao',
                   'query_filter': {'ativa': True, 'pai_id': None}, 'width': 30,
                   'card_path': 'pai.nome', 'filter_path': 'pai.nome'},
        'ordem':  {'type': 'INT', 'width': 8},
        'ativa':          {'type': 'BOOL', 'width': 8},
    },
}

List = {
    'fields': 'Operacao',
    'buttons': [
        {'label': 'Plano', 'icon': 'printer', 'color': 'info',
         'endpoint': 'operacoes.pdf_operacoes'},
    ],
}


def _transformar_nome(nome, pai_id):
    if not pai_id:
        return nome.strip().upper()
    words = nome.strip().split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        else:
            result.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(result)


def _auto_ordem(tipo, pai_id):
    if pai_id:
        return 0
    max_ordem = db.session.query(db.func.max(Operacao.ordem)).filter(
        Operacao.tipo == tipo, Operacao.pai_id.is_(None)
    ).scalar()
    return (max_ordem or 0) + 1


def _operacao_pre_save(instance, request, is_new):
    if instance.fator is None:
        instance.fator = 1
    pai_id = request.form.get("pai_id", type=int) or None
    instance.nome = _transformar_nome(request.form.get("nome", ""), pai_id)
    if is_new or (pai_id is not None and pai_id != instance.pai_id):
        instance.ordem = _auto_ordem(instance.tipo, pai_id)
    instance.pai_id = pai_id
    return True


Form = {
    'fields': 'Operacao',
    'delete': {
        'when': {Operacao},
        'msg_ok': 'Operação excluída!',
        'msg_no': 'Não é possível excluir — existem operações vinculadas.',
    },
    'pre_save': _operacao_pre_save,
    'buttons': [{'on_off': {'field': 'ativa'}}],
}


@auto.rota("/", endpoint='list')
def list():
    from app.reports.operacoes import _build_tree
    secoes = _build_tree()
    op_data = []
    for secao in secoes:
        for item in secao["flat"]:
            op = item["operacao"]
            op.indice = item["indice"]
            op_data.append(op)
    from app.ajsystem.core.do_list import do_list
    return do_list('Operacao', __name__, data=op_data)


@auto.rota("/<int:id>/uso")
def usage(id):
    qtd = Operacao.query.filter_by(pai_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@auto.rota("/pdf")
def pdf_operacoes():
    from app.reports import PLANO
    from app.ajsystem.core.pdf import gerar_pdf_relatorio
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(PLANO, logo_path=logo_path)
    buf = BytesIO()
    pdf.output(buf)
    return Response(
        buf.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "inline; filename=plano_de_contas.pdf"},
    )
