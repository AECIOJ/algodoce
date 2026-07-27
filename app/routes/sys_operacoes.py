import os
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, current_app
from flask_login import login_required
from app.extensions import db
from app.models.operacao import Operacao
from app.constants import TIPO_OPERACAO, CONECTORES
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_boolean_filter, build_fk_options
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form

bp = Blueprint("operacoes", __name__, url_prefix="/operacoes")


OPERACOES_FIELDS = {
        'indice': {'width': 6, 'filter': False, 'pos': 1},
        'id': {'label': '#', 'width': 7, 'mask': '999.999', 'card_path': 'operacao.id'},
        'nome': {'width': 20, 'card_path': 'operacao.nome', 'pos': 1},
        'tipo': {'width': 12, 'options': TIPO_OPERACAO, 'filter_options': TIPO_OPERACAO, 'card_path': 'operacao.tipo'},
        'fator': {'width': 8, 'card_path': 'operacao.fator'},
        'pai_id': {'label': 'Pai', 'width': 30, 'input': 'select', 'query': 'operacao', 'query_filter': {'ativa': True, 'pai_id': None}, 'card_path': 'operacao.pai.nome'},
        'ativa': {'input': 'checkbox', 'card_path': 'operacao.ativa'},
        'ordem': {'width': 8, 'input': 'number', 'card_path': 'operacao.ordem'},
}

operacoes_list = {'fields': OPERACOES_FIELDS, 'edit_endpoint': 'operacoes.form', 'edit_id_field': 'operacao.id'}


def _operacao_pre_save(instance, request, is_new):
    if instance.fator is None:
        instance.fator = 1
    pai_id = request.form.get("pai_id", type=int) or None
    instance.nome = _transformar_nome(request.form.get("nome", ""), pai_id)
    if is_new or (pai_id is not None and pai_id != instance.pai_id):
        instance.ordem = _auto_ordem(instance.tipo, pai_id)
    instance.pai_id = pai_id
    return True


operacoes_form = {'model': Operacao, 'redirect': 'operacoes.list', 'entity_label': 'Operacao', 'fields': OPERACOES_FIELDS, 'pre_save': _operacao_pre_save, 'buttons': [{'label': 'Ativar', 'endpoint': 'operacoes.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': False}}, {'label': 'Desativar', 'endpoint': 'operacoes.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': True}}]}


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
    _list = List(**operacoes_list)
    filter_config = build_filter_config(OPERACOES_FIELDS)
    active = resolve_filters(filter_config, request.args)
    query = Operacao.query.order_by(Operacao.tipo, Operacao.nome)
    _operacoes = query.all()
    linhas = _operacoes[:]
    linhas = apply_boolean_filter(linhas, 'ativa', active.get('ativa'))
    linhas = apply_select_filter(linhas, 'tipo', active.get('tipo'), TIPO_OPERACAO)
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_text_filter(linhas, 'fator', active.get('fator'))
    linhas = apply_select_filter(linhas, 'pai_id', active.get('pai_id'), build_fk_options(Operacao), filter_path='pai.nome')
    linhas = apply_number_filter(linhas, 'ordem', active.get('ordem'))
    operacoes = set(r.id for r in linhas)

    secoes = _build_tree()
    flat_list = []
    for secao in secoes:
        for item in secao["flat"]:
            if item["operacao"].id in operacoes:
                flat_list.append(item)

    ctx = build_field_context(OPERACOES_FIELDS)
    return render_template("sys_operacoes/list.html", operacoes=flat_list, OPERACOES_LIST=_list, ctx=ctx, TIPO_OPERACAO=TIPO_OPERACAO, active_filters=active, FILTERS=filter_config)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    return handle_form(operacoes_form, id)


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
