from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.category import Category
from app.models.product import Product
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_boolean_filter
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form, can_delete
from app.fields import FIELD_ID_SHORT, FIELD_NOME, FIELD_ORDEM, FIELD_ATIVO


CATEGORIAS_FIELDS = {
    'id':    {**FIELD_ID_SHORT, 'pos': 1},
    'nome':  {**FIELD_NOME, 'width': 13, 'pos': 1},
    'ordem': FIELD_ORDEM,
    'ativo': {**FIELD_ATIVO, 'width': 5},
}

categorias_list = {'fields': CATEGORIAS_FIELDS, 'edit_endpoint': 'categories.form'}

bp = Blueprint("categories", __name__, url_prefix="/categorias")


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


categorias_form = {'model': Category, 'redirect': 'categories.list', 'entity_label': 'Categoria', 'fields': CATEGORIAS_FIELDS, 'delete_when': {Product}, 'pre_save': _pre_save, 'post_save': _post_save, 'buttons': [{'label': 'Ativar', 'endpoint': 'categories.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': False}}, {'label': 'Desativar', 'endpoint': 'categories.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': True}}]}


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    _list = List(**categorias_list)
    filter_config = build_filter_config(_list.fields)
    active = resolve_filters(filter_config, request.args)
    query = Category.query.order_by(Category.ordem, Category.nome)
    categorias = query.all()
    linhas = categorias[:]
    linhas = apply_boolean_filter(linhas, 'ativo', active.get('ativo'))
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_number_filter(linhas, 'ordem', active.get('ordem'))
    categorias = linhas
    ctx = build_field_context(_list.master_fields)
    return render_template("sys_categorias/list.html", categorias=categorias,
                           CATEGORIAS_LIST=_list, ctx=ctx,
                           active_filters=active, FILTERS=filter_config)


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    return handle_form(categorias_form, id)


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
