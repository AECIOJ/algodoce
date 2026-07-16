from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.category import Category
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_boolean_filter, MODE_NUMBER, MODE_TEXT, MODE_BOOLEAN
from app.table import Field, build_field_context, Table


CATEGORIES_FIELDS = [
    Field(name='id', label='#', width=3, mask='999',pos=1),
    Field(name='nome', label='Nome', width=13, pos=1),
    Field(name='ordem', label='Ordem', width=5, input='number'),
    Field(name='ativo', label='Ativo', input='boolean', width=5, pos=1),
]

CATEGORIES_TABLE = Table(fields=CATEGORIES_FIELDS, edit_endpoint='categories.edit')

CATEGORIES_FILTERS = {
    'id':     MODE_NUMBER,
    'nome':   MODE_TEXT,
    'ordem':  MODE_NUMBER,
    'ativo':  MODE_BOOLEAN,
}

bp = Blueprint("categories", __name__, url_prefix="/categorias")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    active = resolve_filters(CATEGORIES_FILTERS, request.args)
    query = Category.query.order_by(Category.ordem, Category.nome)
    categorias = query.all()
    linhas = categorias[:]
    linhas = apply_boolean_filter(linhas, 'ativo', active.get('ativo'))
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_number_filter(linhas, 'ordem', active.get('ordem'))
    categorias = linhas
    ctx = build_field_context(CATEGORIES_FIELDS, {})
    return render_template("sys_categories/list.html", categorias=categorias,
                           CATEGORIES_TABLE=CATEGORIES_TABLE, ctx=ctx, active_filters=active, FILTERS=CATEGORIES_FILTERS)


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
    return render_template("sys_categories/form.html", fields=CATEGORIES_FIELDS)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    category = Category.query.get(id)
    if not category:
        flash("Código inexistente", "warning")
        return redirect(url_for("categories.list"))
    if request.method == "POST":
        category.nome = request.form["nome"]
        category.ativo = request.form.get("ativo") in ("on", "1", 1, True)
        category.ordem = request.form.get("ordem", 0, type=int)
        db.session.commit()
        flash("Categoria atualizada!", "success")
        return redirect(url_for("categories.list"))

    query = Category.query.with_entities(Category.id).order_by(Category.id)
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

    return render_template("sys_categories/form.html", category=category, nav=nav, fields=CATEGORIES_FIELDS)


@bp.route("/<int:id>/uso")
def usage(id):
    from app.models.product import Product
    qtd = Product.query.filter_by(category_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    from app.models.product import Product
    category = Category.query.get_or_404(id)
    usage = Product.query.filter_by(category_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{category.nome}' — está em {usage} produto(s). "
            f"Remova a categoria dos produtos primeiro.",
            "danger",
        )
        return redirect(url_for("categories.edit", id=id))
    db.session.delete(category)
    db.session.commit()
    flash("Categoria excluída!", "success")
    return redirect(url_for("categories.list"))


@bp.route("/<int:id>/toggle")
def toggle(id):
    category = Category.query.get_or_404(id)
    category.ativo = not category.ativo
    db.session.commit()
    flash("Categoria atualizada!", "success")
    return redirect(url_for("categories.edit", id=id))
