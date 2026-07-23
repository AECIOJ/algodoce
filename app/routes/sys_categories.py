from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_boolean_filter, MODE_NUMBER, MODE_TEXT, MODE_BOOLEAN
from app.table import Field, build_field_context, Table
from app.form import Form, handle_form


CATEGORIES_FIELDS = [
    Field(name='id', label='#', width=3, mask='999', pos=1),
    Field(name='nome', label='Nome', width=13, pos=1),
    Field(name='ordem', label='Ordem', width=5, input='number'),
    Field(name='ativo', label='Ativo', input='boolean', width=5, pos=1),
]

CATEGORIES_TABLE = Table(fields=CATEGORIES_FIELDS, edit_endpoint='categories.form')

CATEGORIES_FILTERS = {
    'id':     MODE_NUMBER,
    'nome':   MODE_TEXT,
    'ordem':  MODE_NUMBER,
    'ativo':  MODE_BOOLEAN,
}

def categories_pre_save(instance, form, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1


def renumber_categories(instance, changed, old_vals):
    if 'ordem' not in changed:
        return
    others = Category.query.filter(Category.id != instance.id).order_by(Category.ordem, Category.nome).all()
    n = instance.ordem
    if n is None or n > len(others) + 1:
        ordered = others + [instance]
    else:
        ordered = others[:n-1] + [instance] + others[n-1:]
    for i, cat in enumerate(ordered, 1):
        cat.ordem = i
    db.session.commit()


CATEGORIAS_FORM = Form(
    model=Category,
    redirect='categories.list',
    fields=[
        Field('nome', required=True, width=6),
        Field('ordem', input='number', width=3, attrs={'min': 0, 'max': 99}),
    ],
    delete_enabled=True,
    delete_check_usage=lambda id: Product.query.filter_by(category_id=id).count(),
    pre_save=categories_pre_save,
    post_save=renumber_categories,
)

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
                           CATEGORIES_TABLE=CATEGORIES_TABLE, ctx=ctx,
                           active_filters=active, FILTERS=CATEGORIES_FILTERS)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    return handle_form(CATEGORIAS_FORM, id)


@bp.route("/<int:id>/uso")
def usage(id):
    qtd = Product.query.filter_by(category_id=id).count()
    return jsonify({"em_uso": qtd > 0, "quantidade": qtd})


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    category = Category.query.get_or_404(id)
    usage = Product.query.filter_by(category_id=id).count()
    if usage > 0:
        flash(
            f"Não é possível excluir '{category.nome}' — está em {usage} produto(s). "
            f"Remova a categoria dos produtos primeiro.",
            "danger",
        )
        return redirect(url_for("categories.form", id=id))
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
    return redirect(url_for("categories.form", id=id))
