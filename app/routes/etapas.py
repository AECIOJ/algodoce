from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.etapa import Etapa

bp = Blueprint("etapas", __name__, url_prefix="/etapas")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    etapas = Etapa.query.order_by(Etapa.ordem, Etapa.nome).all()
    return render_template("etapas/list.html", etapas=etapas)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        etapa = Etapa(
            nome=request.form["nome"],
            ordem=request.form.get("ordem", 0, type=int),
        )
        db.session.add(etapa)
        db.session.commit()
        flash("Etapa cadastrada!", "success")
        return redirect(url_for("etapas.list"))
    return render_template("etapas/form.html")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    etapa = Etapa.query.get(id)
    if not etapa:
        flash("Código inexistente", "warning")
        return redirect(url_for("etapas.list"))
    if request.method == "POST":
        etapa.nome = request.form["nome"]
        etapa.ordem = request.form.get("ordem", 0, type=int)
        db.session.commit()
        flash("Etapa atualizada!", "success")
        return redirect(url_for("etapas.list"))

    query = Etapa.query.with_entities(Etapa.id).order_by(Etapa.id)
    ids = [e.id for e in query.all()]
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

    return render_template("etapas/form.html", etapa=etapa, nav=nav)


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    etapa = Etapa.query.get_or_404(id)
    db.session.delete(etapa)
    db.session.commit()
    flash("Etapa excluída!", "success")
    return redirect(url_for("etapas.list"))
