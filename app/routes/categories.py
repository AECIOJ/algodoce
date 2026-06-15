from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.category import Category

bp = Blueprint("categories", __name__, url_prefix="/categorias")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    categorias = Category.query.order_by(Category.ordem, Category.nome).all()
    return render_template("categories/list.html", categorias=categorias)


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        category = Category(
            nome=request.form["nome"],
            ativo=request.form.get("ativo") in ("on", "1", 1, True),
            ordem=request.form.get("ordem", 0, type=int),
        )
        db.session.add(category)
        db.session.commit()
        flash("Categoria cadastrada!", "success")
        return redirect(url_for("categories.list"))
    return render_template("categories/form.html")


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    category = Category.query.get_or_404(id)
    if request.method == "POST":
        category.nome = request.form["nome"]
        category.ativo = request.form.get("ativo") in ("on", "1", 1, True)
        category.ordem = request.form.get("ordem", 0, type=int)
        db.session.commit()
        flash("Categoria atualizada!", "success")
        return redirect(url_for("categories.list"))

    query = Category.query.with_entities(Category.id).order_by(Category.ordem, Category.nome)
    ids = [c.id for c in query.all()]
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

    return render_template("categories/form.html", category=category, nav=nav)


@bp.route("/<int:id>/toggle")
def toggle(id):
    category = Category.query.get_or_404(id)
    category.ativo = not category.ativo
    db.session.commit()
    flash("Categoria atualizada!", "success")
    return redirect(url_for("categories.edit", id=id))
