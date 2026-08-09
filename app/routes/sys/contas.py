from flask import request, jsonify, flash
from app.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.constantes import ORDER_STATUS, TIPO_CONTA
from app.ajsystem.engine import auto


Entity = {
    'Conta': {
        'id':             {'type': 'ID', 'width': 7},
        'nome':           {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':           {'type': 'LIST', 'width': 12, 'list': TIPO_CONTA},
        'telefone':       {'type': 'FONE', 'required': True},
        'email':          {'type': 'TEXT', 'input': 'email', 'required': True},
        'cpf':            {'type': 'CPF'},
        'cnpj':           {'type': 'CNPJ'},
        'insc_estadual':  {'type': 'TEXT', 'required': False},
        'endereco':       {'type': 'TEXT', 'input': 'textarea', 'required': True},
        'ativo':          {'type': 'BOOL'},
    },
}

List = {
    'fields': [
        'Conta.id',
        'Conta.nome',
        'Conta.tipo',
        'Conta.telefone',
        'Conta.ativo',
    ],
}


def contas_pre_save(instance, request, is_new):
    cpf = request.form.get("cpf", "").strip() or None
    cnpj = request.form.get("cnpj", "").strip() or None
    if cpf and cnpj:
        flash("Preencha apenas CPF ou CNPJ, não ambos.", "warning")
        return False
    instance.insc_estadual = (request.form.get("insc_estadual", "").strip() or None) if cnpj else None


def _pre_get(mod, id):
    ctx = {'ORDER_STATUS': ORDER_STATUS}
    if id is not None:
        conta = Conta.query.get(id)
        if conta:
            ctx['orders'] = conta.orders.order_by(Order.data_pedido.desc()).all()
    return ctx


Form = {
    'fields': 'Conta',
    'sessions': {'Pedidos': {'type': 'template', 'template': 'sys_contas/_orders.html'}},
    'pre_save': contas_pre_save,
    'pre_get': _pre_get,
    'buttons': ['on_off'],
}


@auto.rota("/search", methods=["GET"])
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
