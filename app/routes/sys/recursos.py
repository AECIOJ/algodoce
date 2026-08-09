from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.recurso import Recurso
from app.constantes import TIPO_RECURSO
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter
from app.ajsystem.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form
from app.fields import FIELD_ID, FIELD_NOME, FIELD_TIPO, FIELD_VALOR, FIELD_DATA


RECURSOS_FIELDS = {'model': Recurso, 'fields': {
    'id':    {**FIELD_ID, 'width': 7},
    'nome':  {**FIELD_NOME, 'width': 20},
    'tipo':  {**FIELD_TIPO, 'width': 12, 'options': TIPO_RECURSO, 'required': True},
    'saldo': {**FIELD_VALOR, 'label': 'Saldo Inicial', 'width': 12},
    'data':  {**FIELD_DATA, 'label': 'Balanço', 'width': 12},
}}

recursos_list = {'fields': RECURSOS_FIELDS, 'edit_endpoint': 'recursos.form'}

bp = Blueprint("recursos", __name__, url_prefix="/recursos")


@bp.route("/")
@login_required
def list():
    _list = List(**recursos_list)
    filter_config = build_filter_config(_list.fields)
    active = resolve_filters(filter_config, request.args)
    query = Recurso.query
    recursos = query.order_by(Recurso.nome).all()
    linhas = recursos[:]
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_select_filter(linhas, 'tipo', active.get('tipo'), TIPO_RECURSO)
    linhas = apply_number_filter(linhas, 'saldo', active.get('saldo'))
    linhas = apply_date_filter(linhas, 'data', active.get('data'))
    recursos = linhas
    ctx = build_field_context(_list.fields)
    return render_template("index.html")


Form = {'model': Recurso, 'redirect': 'recursos.list', 'fields': RECURSOS_FIELDS}


@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def form(id):
    return handle_form(Form, id)