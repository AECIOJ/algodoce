from flask import request, jsonify, flash
from app.ajsystem.core.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.constantes import ORDER_STATUS, TIPO_CONTA
from app.ajsystem.core import auto


Entity = {
    'Conta': {
        'id':             {'type': 'ID', 'width': 7},
        'nome':           {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':           {'type': 'LIST', 'width': 12, 'list': TIPO_CONTA},
        'telefone':       {'type': 'FONE', 'required': True},
        'email':          {'type': 'TEXT', 'input': 'email', 'width': 50},
        'cpf':            {'type': 'CPF', 'label': 'CPF'},
        'cnpj':           {'type': 'CNPJ', 'label': 'CNPJ'},
        'insc_estadual':  {'type': 'TEXT', 'label': 'Insc. Estadual', },
        'endereco':       {'type': 'TEXT', 'label': 'Endereço', 'input': 'textarea',  'in_list': 2},
        'ativo':          {'type': 'BOOL'},
    },
    'Order': {
        'id':           {'type': 'ID', 'width': 6},
        'client_id':    {'type': 'DK', 'label': 'Cliente'},
        'data_pedido':  {'type': 'DATA_HORA', 'label': 'Data Pedido', 'width': 12},
        'data_entrega': {'type': 'DATA', 'label': 'Data Entrega', 'width': 11},
        'total':        {'type': 'NUM', 'currency': True},
        'status':       {'type': 'LIST', 'list': ORDER_STATUS, 'width': 11},
        'qtd':          {'type': 'INT', 'derived': {'sum': 'items.quantidade'}},
    },
}

Query = {
    'pedidos': {
        'fields': ['Order'],
        'group_by': 'status',
        'order_by': 'data_pedido desc',
        'totals': {
            'Qtd':          {'sum': 'qtd'},
            'Valor':        {'sum': 'total', 'currency': True},
            'Média/Pedido': {'avg': 'total', 'currency': True},
            'Média/Item':   {'avg': 'total', 'by': 'qtd', 'currency': True},
        },
    },
}


def contas_pre_save(instance, request, is_new):
    cpf = request.form.get("cpf", "").strip() or None
    cnpj = request.form.get("cnpj", "").strip() or None
    if cpf and cnpj:
        flash("Preencha apenas CPF ou CNPJ, não ambos.", "warning")
        return False
    instance.insc_estadual = (request.form.get("insc_estadual", "").strip() or None) if cnpj else None


Page = {
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'fields': 'Conta',
            'ordering': ['nome'],
        },
        'form': {
            'fields': 'Conta',
            'sessions': {'Pedidos': {'query': 'pedidos'}},
            'pre_save': contas_pre_save,
            'buttons': ['on_off'],
        },
    },
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
