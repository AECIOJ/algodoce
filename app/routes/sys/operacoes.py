import os
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from flask_login import login_required
from app.extensions import db
from app.models.operacao import Operacao
from app.constants import TIPO_OPERACAO, CONECTORES
from app.form import handle_form
from app.engine.handle_list import render_list


Entidade = {
    'Operacao': {
        'id':     {'type': 'PK', 'width': 6},
        'indice': {'width': 6, 'filter': False, 'edit': False},
        'nome':   {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':   {'type': 'LIST', 'width': 12, 'list': TIPO_OPERACAO},
        'fator':  {'type': 'INT', 'width': 8},
        'pai_id': {'type': 'FK', 'query': 'operacao',
                   'query_filter': {'ativa': True, 'pai_id': None}, 'width': 30,
                   'card_path': 'pai.nome', 'filter_path': 'pai.nome'},
        'ordem':  {'type': 'INT', 'width': 8},
        'ativa':  {'type': 'BOOL', 'width': 8},
    },
}

Lista = {
    'colunas': ['Operacao'],
    'new_endpoint': 'operacoes.form',
    'edit_endpoint': 'operacoes.form',
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
    'pre_save': _operacao_pre_save,
    'buttons': [
        {'label': 'Ativar', 'endpoint': 'operacoes.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativa': False}},
        {'label': 'Desativar', 'endpoint': 'operacoes.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativa': True}},
    ],
}


bp = Blueprint("operacoes", __name__, url_prefix="/operacoes")


from app.reports.rep_operacao import _build_tree


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/plano")
def plano():
    secoes = _build_tree()
    return render_template("sys_operacoes/plano.html", secoes=secoes, TIPO_OPERACAO=TIPO_OPERACAO)


@bp.route("/")
def list():
    from app.reports.rep_operacao import _build_tree
    secoes = _build_tree()
    op_data = []
    for secao in secoes:
        for item in secao["flat"]:
            op = item["operacao"]
            op.indice = item["indice"]
            op_data.append(op)
    return render_list('Operacao', __name__, data=op_data)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    return handle_form(Form, id)


@bp.route("/<int:id>/uso")
def usage(id):
    qtd = Operacao.query.filter_by(pai_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    operacao = Operacao.query.get_or_404(id)
    usage = Operacao.query.filter_by(pai_id=id).count()
    if usage > 0:
        flash(
            f"Nao e possivel excluir '{operacao.nome}' — {usage} operacao(es) estao vinculadas. "
            f"Remova os vinculos primeiro.",
            "danger",
        )
        return redirect(url_for("operacoes.form", id=id))
    db.session.delete(operacao)
    db.session.commit()
    flash("Operacao excluida!", "success")
    return redirect(url_for("operacoes.list"))


@bp.route("/<int:id>/toggle")
def toggle(id):
    operacao = Operacao.query.get_or_404(id)
    operacao.ativa = not operacao.ativa
    db.session.commit()
    flash("Operacao atualizada!", "success")
    return redirect(url_for("operacoes.form", id=id))


@bp.route("/print")
def print_operacoes():
    from app.reports.rep_operacao import OPERACAO_REPORT
    return render_template(
        OPERACAO_REPORT.print_template,
        fallback_url=url_for("operacoes.list"),
        pdf_url=url_for("operacoes.pdf_operacoes"),
    )


@bp.route("/pdf")
def pdf_operacoes():
    from app.reports.rep_operacao import OPERACAO_REPORT
    from app.pdf import gerar_pdf_relatorio
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(OPERACAO_REPORT, logo_path=logo_path)
    buf = BytesIO()
    pdf.output(buf)
    return Response(
        buf.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": "inline; filename=operacoes.pdf"},
    )
