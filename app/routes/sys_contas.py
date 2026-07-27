import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.constants import ORDER_STATUS, TIPO_CONTA
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_boolean_filter
from app.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form
from app.fields import FIELD_ID, FIELD_NOME, FIELD_TIPO, FIELD_TELEFONE, FIELD_EMAIL, FIELD_CPF, FIELD_CNPJ, FIELD_ENDERECO, FIELD_ATIVO


CONTAS_FIELDS = {'model': Conta, 'fields': {
    'id':             {**FIELD_ID, 'width': 7},
    'nome':           {**FIELD_NOME, 'width': 20},
    'tipo':           {**FIELD_TIPO, 'width': 12, 'options': TIPO_CONTA},
    'telefone':       {**FIELD_TELEFONE},
    'email':          FIELD_EMAIL,
    'cpf':            FIELD_CPF,
    'cnpj':           FIELD_CNPJ,
    'insc_estadual':  {'label': 'Inscrição Estadual'},
    'endereco':       FIELD_ENDERECO,
    'ativo':          FIELD_ATIVO,
}}

contas_list = {'fields': CONTAS_FIELDS, 'edit_endpoint': 'contas.form'}

bp = Blueprint("contas", __name__)


def _cpf_valido(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 11 or s == s[0] * 11:
        return False
    soma = sum(int(s[i]) * (10 - i) for i in range(9))
    d1 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    if d1 != int(s[9]):
        return False
    soma = sum(int(s[i]) * (11 - i) for i in range(10))
    d2 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    return d2 == int(s[10])


def _cnpj_valido(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 14 or s == s[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w1[i] for i in range(12))
    d1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if d1 != int(s[12]):
        return False
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w2[i] for i in range(13))
    d2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return d2 == int(s[13])


def contas_pre_save(instance, request, is_new):
    cpf = request.form.get("cpf", "").strip() or None
    cnpj = request.form.get("cnpj", "").strip() or None
    if cpf and cnpj:
        flash("Preencha apenas CPF ou CNPJ, não ambos.", "warning")
        return False
    if cpf and not _cpf_valido(cpf):
        flash("CPF inválido.", "warning")
        return False
    if cnpj and not _cnpj_valido(cnpj):
        flash("CNPJ inválido.", "warning")
        return False
    instance.cpf = cpf
    instance.cnpj = cnpj
    instance.insc_estadual = (request.form.get("insc_estadual", "").strip() or None) if cnpj else None


contas_form = {'model': Conta, 'redirect': 'contas.list', 'entity_label': 'Conta', 'page_scripts': 'sys_contas/_form_scripts.html', 'fields': CONTAS_FIELDS, 'sessions': {'Pedidos': {'type': 'template', 'template': 'sys_contas/_orders.html'}}, 'pre_save': contas_pre_save, 'buttons': [{'label': 'Ativar', 'endpoint': 'contas.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': False}}, {'label': 'Desativar', 'endpoint': 'contas.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': True}}]}


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/contas")
def list():
    _list = List(**contas_list)
    filter_config = build_filter_config(CONTAS_FIELDS)
    active = resolve_filters(filter_config, request.args)
    query = Conta.query.order_by(Conta.nome)
    contas = query.all()
    linhas = contas[:]
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'nome', active.get('nome'))
    linhas = apply_select_filter(linhas, 'tipo', active.get('tipo'), TIPO_CONTA)
    linhas = apply_text_filter(linhas, 'telefone', active.get('telefone'))
    linhas = apply_boolean_filter(linhas, 'ativo', active.get('ativo'))
    contas = linhas
    ctx = build_field_context(_list.fields)
    return render_template("sys_contas/list.html", contas=contas, CONTAS_LIST=_list, ctx=ctx, TIPO_CONTA=TIPO_CONTA, active_filters=active, FILTERS=filter_config)


@bp.route("/contas/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    contas = (
        Conta.query
        .filter(Conta.nome.ilike(f"%{q}%"))
        .order_by(Conta.nome)
        .limit(10)
        .all()
    )
    return jsonify([{"id": c.id, "nome": c.nome} for c in contas])


@bp.route("/contas/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/contas/<int:id>/editar", methods=["GET", "POST"])
def form(id):
    orders = []
    if id is not None:
        conta = Conta.query.get(id)
        if conta:
            orders = conta.orders.order_by(Order.data_pedido.desc()).all()
    return handle_form(contas_form, id, extra_ctx={'orders': orders, 'ORDER_STATUS': ORDER_STATUS})


@bp.route("/contas/<int:id>/toggle")
def toggle(id):
    conta = Conta.query.get_or_404(id)
    conta.ativo = not conta.ativo
    db.session.commit()
    flash("Conta atualizada!", "success")
    return redirect(url_for("contas.form", id=id))