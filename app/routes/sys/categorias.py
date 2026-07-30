from flask import Blueprint, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.form import handle_form, can_delete
from app.engine.handle_list import render_list


Entidade = {
    'Category': {
        'id':    {'type': 'PK', 'width': 6},
        'nome':  {'type': 'TEXT'},
        'ordem': {'type': 'INT', 'mask': '999', 'attrs': {'min': 0, 'max': 99}},
        'ativo': {'type': 'BOOL'},
    },
}

Lista = {
    'colunas': ['Category'],
    'ordering': ['ordem', 'nome'],
    'title': 'Categorias',
    'edit_endpoint': 'categories.form',
    'new_endpoint': 'categories.form',
}


def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1


def _post_save(instance, changed, old_vals):
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


Form = {
    'fields': 'Category',
    'delete_when': {Product},
    'pre_save': _pre_save,
    'post_save': _post_save,
    'buttons': [
        {'label': 'Ativar', 'endpoint': 'categories.toggle',
         'icon': 'bi-toggle-on', 'color': 'success', 'outline': True,
         'position': 'nav_right', 'show_if': {'ativo': False}},
        {'label': 'Desativar', 'endpoint': 'categories.toggle',
         'icon': 'bi-toggle-off', 'color': 'success', 'outline': True,
         'position': 'nav_right', 'show_if': {'ativo': True}},
    ],
}


bp = Blueprint("categories", __name__, url_prefix="/categorias")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    return render_list('Category', __name__)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    return handle_form(Form, id)


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    category = Category.query.get_or_404(id)
    if not can_delete(category, {Product}):
        flash(f"Não é possível excluir '{category.nome}' — está em uso.", "danger")
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
