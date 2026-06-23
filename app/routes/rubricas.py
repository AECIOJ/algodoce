from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.rubrica import Rubrica
from app.constants import TIPO_RUBRICA

bp = Blueprint("rubricas", __name__, url_prefix="/rubricas")


def _auto_ordem(tipo, pai_id):
    if pai_id:
        return 0
    max_ordem = db.session.query(db.func.max(Rubrica.ordem)).filter(
        Rubrica.tipo == tipo, Rubrica.pai_id.is_(None)
    ).scalar()
    return (max_ordem or 0) + 1


def _build_tree():
    todas = Rubrica.query.order_by(Rubrica.ordem, Rubrica.id).all()
    filhos = {}
    for r in todas:
        filhos.setdefault(r.pai_id, []).append(r)

    def _build(pid, tipo):
        items = []
        for r in sorted(filhos.get(pid, []), key=lambda x: (x.ordem, x.id)):
            if r.tipo != tipo:
                continue
            item = {"rubrica": r, "filhos": _build(r.id, tipo)}
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
    for tipo_num in sorted(TIPO_RUBRICA):
        tree = _build(None, tipo_num)
        if tree:
            flat = _assign(tree, str(tipo_num))
            secoes.append({"tipo": tipo_num, "label": TIPO_RUBRICA[tipo_num], "tree": tree, "flat": flat})
    return secoes


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/plano")
def plano():
    secoes = _build_tree()
    return render_template("rubricas/plano.html", secoes=secoes, TIPO_RUBRICA=TIPO_RUBRICA)


@bp.route("/")
def list():
    status = request.args.get("status", "todos")
    query = Rubrica.query.order_by(Rubrica.tipo, Rubrica.nome)
    if status == "ativos":
        query = query.filter_by(ativa=True)
    elif status == "inativos":
        query = query.filter_by(ativa=False)
    rubricas = set(r.id for r in query.all())

    secoes = _build_tree()
    flat_list = []
    for secao in secoes:
        for item in secao["flat"]:
            if item["rubrica"].id in rubricas:
                flat_list.append(item)

    return render_template("rubricas/list.html", rubricas=flat_list, status=status, TIPO_RUBRICA=TIPO_RUBRICA)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        pai_id = request.form.get("pai_id", type=int) or None
        rubrica = Rubrica(
            nome=request.form["nome"],
            tipo=request.form["tipo"],
            pai_id=pai_id,
            ordem=_auto_ordem(request.form["tipo"], pai_id),
            fator=request.form.get("fator", 1, type=int),
            ativa=request.form.get("ativa") in ("on", "1", 1, True),
        )
        db.session.add(rubrica)
        db.session.commit()
        flash("Rubrica cadastrada!", "success")
        return redirect(url_for("rubricas.list"))
    paises = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.tipo, Rubrica.nome).all()
    return render_template("rubricas/form.html", TIPO_RUBRICA=TIPO_RUBRICA, paises=paises)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    rubrica = Rubrica.query.get(id)
    if not rubrica:
        flash("Código inexistente", "warning")
        return redirect(url_for("rubricas.list"))
    if request.method == "POST":
        rubrica.nome = request.form["nome"]
        rubrica.tipo = request.form["tipo"]
        pai_id = request.form.get("pai_id", type=int) or None
        if rubrica.pai_id != pai_id:
            rubrica.pai_id = pai_id
            rubrica.ordem = _auto_ordem(rubrica.tipo, pai_id)
        rubrica.fator = request.form.get("fator", 1, type=int)
        rubrica.ativa = request.form.get("ativa") in ("on", "1", 1, True)
        db.session.commit()
        flash("Rubrica atualizada!", "success")
        return redirect(url_for("rubricas.list"))

    query = Rubrica.query.with_entities(Rubrica.id).order_by(Rubrica.id)
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

    paises = Rubrica.query.filter(Rubrica.ativa == True, Rubrica.id != id).order_by(Rubrica.tipo, Rubrica.nome).all()
    return render_template("rubricas/form.html", rubrica=rubrica, nav=nav, TIPO_RUBRICA=TIPO_RUBRICA, paises=paises)


@bp.route("/<int:id>/uso")
def usage(id):
    qtd = Rubrica.query.filter_by(pai_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    rubrica = Rubrica.query.get_or_404(id)
    usage = Rubrica.query.filter_by(pai_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{rubrica.nome}' — {usage} rubrica(s) estão vinculadas. "
            f"Remova os vínculos primeiro.",
            "danger",
        )
        return redirect(url_for("rubricas.edit", id=id))
    db.session.delete(rubrica)
    db.session.commit()
    flash("Rubrica excluída!", "success")
    return redirect(url_for("rubricas.list"))


@bp.route("/<int:id>/toggle")
def toggle(id):
    rubrica = Rubrica.query.get_or_404(id)
    rubrica.ativa = not rubrica.ativa
    db.session.commit()
    flash("Rubrica atualizada!", "success")
    return redirect(url_for("rubricas.edit", id=id))
