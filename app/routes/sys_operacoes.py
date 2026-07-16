from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.operacao import Operacao
from app.constants import TIPO_OPERACAO, CONECTORES
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_boolean_filter, build_fk_options, MODE_NUMBER, MODE_TEXT, MODE_BOOLEAN, MODE_SELECT
from app.table import Field, build_field_context, Table

bp = Blueprint("operacoes", __name__, url_prefix="/operacoes")


OPERACOES_FIELDS = [
    Field(name='indice', label='Indice', width=6, filter=False, pos=1),
    Field(name='id', label='#', width=7, mask='999.999', card_path='operacao.id'),
    Field(name='nome', label='Nome', width=20, card_path='operacao.nome', pos=1),
    Field(name='tipo', label='Tipo', width=12, options=TIPO_OPERACAO, filter_options=TIPO_OPERACAO, card_path='operacao.tipo'),
    Field(name='fator', label='Fator', width=8, card_path='operacao.fator'),
    Field(name='pai', label='Pai', width=30, query='operacao', card_path='operacao.pai.nome'),
    Field(name='ativa', label='Ativa', input='boolean', card_path='operacao.ativa'),
    Field(name='ordem', label='Ordem', width=8, input='number', card_path='operacao.ordem'),
]

OPERACOES_TABLE = Table(fields=OPERACOES_FIELDS, edit_endpoint='operacoes.edit', edit_id_field='operacao.id')

OPERACOES_FILTERS = {
    'id':     MODE_NUMBER,
    'nome':   MODE_TEXT,
    'tipo':   {**MODE_SELECT, 'options': TIPO_OPERACAO},
    'fator':  MODE_TEXT,
    'pai':    {**MODE_SELECT, 'filter_path': 'pai.nome'},
    'ativa':  MODE_BOOLEAN,
    'ordem':  MODE_NUMBER,
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
    active = resolve_filters(OPERACOES_FILTERS, request.args)
    query = Operacao.query.order_by(Operacao.tipo, Operacao.nome)
    operacoes_list = query.all()
    linhas = operacoes_list[:]
    linhas = apply_boolean_filter(linhas, 'ativa', active.get('ativa'))
    linhas = apply_select_filter(linhas, 'tipo', active.get('tipo'), TIPO_OPERACAO)
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_text_filter(linhas, 'fator', active.get('fator'))
    linhas = apply_select_filter(linhas, 'pai', active.get('pai'), build_fk_options(Operacao), filter_path='pai.nome')
    linhas = apply_number_filter(linhas, 'ordem', active.get('ordem'))
    operacoes = set(r.id for r in linhas)

    secoes = _build_tree()
    flat_list = []
    for secao in secoes:
        for item in secao["flat"]:
            if item["operacao"].id in operacoes:
                flat_list.append(item)

    ctx = build_field_context(OPERACOES_FIELDS, filters_config=OPERACOES_FILTERS)
    return render_template("sys_operacoes/list.html", operacoes=flat_list, OPERACOES_TABLE=OPERACOES_TABLE, ctx=ctx, TIPO_OPERACAO=TIPO_OPERACAO, active_filters=active, FILTERS=OPERACOES_FILTERS)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        pai_id = request.form.get("pai_id", type=int) or None
        nome = _transformar_nome(request.form["nome"], pai_id)
        operacao = Operacao(
            nome=nome,
            tipo=request.form["tipo"],
            pai_id=pai_id,
            ordem=_auto_ordem(request.form["tipo"], pai_id),
            fator=request.form.get("fator", 1, type=int),
            ativa=request.form.get("ativa") in ("on", "1", 1, True),
        )
        db.session.add(operacao)
        db.session.commit()
        flash("Operacao cadastrada!", "success")
        return redirect(url_for("operacoes.list"))
    paises = Operacao.query.filter(Operacao.ativa == True, Operacao.pai_id.is_(None)).order_by(Operacao.tipo, Operacao.nome).all()
    return render_template("sys_operacoes/form.html", TIPO_OPERACAO=TIPO_OPERACAO, paises=paises)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    operacao = Operacao.query.get(id)
    if not operacao:
        flash("Codigo inexistente", "warning")
        return redirect(url_for("operacoes.list"))
    if request.method == "POST":
        pai_id = request.form.get("pai_id", type=int) or None
        operacao.nome = _transformar_nome(request.form["nome"], pai_id)
        operacao.tipo = request.form["tipo"]
        if operacao.pai_id != pai_id:
            operacao.pai_id = pai_id
            operacao.ordem = _auto_ordem(operacao.tipo, pai_id)
        operacao.fator = request.form.get("fator", 1, type=int)
        operacao.ativa = request.form.get("ativa") in ("on", "1", 1, True)
        db.session.commit()
        flash("Operacao atualizada!", "success")
        return redirect(url_for("operacoes.list"))

    query = Operacao.query.with_entities(Operacao.id).order_by(Operacao.id)
    ids = [r.id for r in query.all()]
    try:
        current_idx = ids.index(id)
        nav = {
            "first_id": ids[0],
            "last_id": ids[-1],
            "prev_id": ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": ids[current_idx + 1] if current_idx < len(ids) - 1 else None,
        }
    except ValueError:
        nav = {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}

    paises = Operacao.query.filter(Operacao.ativa == True, Operacao.id != id, Operacao.pai_id.is_(None)).order_by(Operacao.tipo, Operacao.nome).all()
    return render_template("sys_operacoes/form.html", operacao=operacao, nav=nav, TIPO_OPERACAO=TIPO_OPERACAO, paises=paises)


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
        return redirect(url_for("operacoes.edit", id=id))
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
    return redirect(url_for("operacoes.edit", id=id))
