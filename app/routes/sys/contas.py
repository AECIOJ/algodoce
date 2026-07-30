import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.constants import ORDER_STATUS, TIPO_CONTA
from app.form import handle_form
from app.engine.handle_list import render_list


Entidade = {
    'Conta': {
        'id':             {'type': 'PK', 'width': 7},
        'nome':           {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':           {'type': 'LIST', 'width': 12, 'list': TIPO_CONTA},
        'telefone':       {'type': 'TEXT', 'width': 14, 'mask': '(99) 99999-9999', 'required': True},
        'email':          {'type': 'TEXT', 'input': 'email', 'required': True},
        'cpf':            {'type': 'TEXT', 'mask': '999.999.999-99'},
        'cnpj':           {'type': 'TEXT', 'mask': '99.999.999/9999-99'},
        'insc_estadual':  {'type': 'TEXT'},
        'endereco':       {'type': 'TEXT', 'input': 'textarea', 'required': True},
        'ativo':          {'type': 'BOOL'},
    },
}

Lista = {
    'colunas': [
        'Conta.id',
        'Conta.nome',
        'Conta.tipo',
        'Conta.telefone',
        'Conta.ativo',
    ],
    'new_endpoint': 'contas.form',
    'edit_endpoint': 'contas.form',
}


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


Form = {
    'fields': 'Conta',
    'page_scripts': 'sys_contas/_form_scripts.html',
    'sessions': {'Pedidos': {'type': 'template', 'template': 'sys_contas/_orders.html'}},
    'pre_save': contas_pre_save,
    'buttons': [
        {'label': 'Ativar', 'endpoint': 'contas.toggle', 'icon': 'bi-toggle-on', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': False}},
        {'label': 'Desativar', 'endpoint': 'contas.toggle', 'icon': 'bi-toggle-off', 'color': 'success', 'outline': True, 'position': 'nav_right', 'show_if': {'ativo': True}},
    ],
}


bp = Blueprint("contas", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/contas/")
@bp.route("/contas")
def list():
    return render_list('Conta', __name__)


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
    return handle_form(Form, id, extra_ctx={'orders': orders, 'ORDER_STATUS': ORDER_STATUS})


@bp.route("/contas/<int:id>/toggle")
def toggle(id):
    conta = Conta.query.get_or_404(id)
    conta.ativo = not conta.ativo
    db.session.commit()
    flash("Conta atualizada!", "success")
    return redirect(url_for("contas.form", id=id))