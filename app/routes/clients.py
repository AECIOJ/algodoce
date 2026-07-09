import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.constants import ORDER_STATUS, TIPO_CONTA
from app.fields import Field, build_field_context


CONTAS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='nome', label='Nome', width=20, pos=1),
    Field(name='tipo', label='Tipo', width=12, options=TIPO_CONTA, filter_options=list(TIPO_CONTA.values())),
    Field(name='telefone', label='Telefone', width=14),
    Field(name='ativo', label='Ativo', input='boolean', pos=1),
]

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


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/contas")
def list():
    tipo = request.args.get("tipo", "todos")
    query = Conta.query.order_by(Conta.nome)
    if tipo == "clientes":
        query = query.filter(Conta.tipo.in_([0, 1]))
    elif tipo == "fornecedores":
        query = query.filter(Conta.tipo.in_([1, 2]))
    contas = query.all()
    ctx = build_field_context(CONTAS_FIELDS)
    return render_template("contas/list.html", contas=contas, fields=CONTAS_FIELDS, ctx=ctx, TIPO_CONTA=TIPO_CONTA)


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


@bp.route("/contas/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        cpf = request.form.get("cpf", "").strip() or None
        cnpj = request.form.get("cnpj", "").strip() or None
        insc_estadual = request.form.get("insc_estadual", "").strip() or None
        if cpf and cnpj:
            flash("Preencha apenas CPF ou CNPJ, não ambos.", "warning")
            return render_template("contas/form.html", conta=None, TIPO_CONTA=TIPO_CONTA)
        if cpf and not _cpf_valido(cpf):
            flash("CPF inválido.", "warning")
            return render_template("contas/form.html", conta=None, TIPO_CONTA=TIPO_CONTA)
        if cnpj and not _cnpj_valido(cnpj):
            flash("CNPJ inválido.", "warning")
            return render_template("contas/form.html", conta=None, TIPO_CONTA=TIPO_CONTA)
        conta = Conta(
            nome=request.form["nome"],
            email=(request.form["email"] or None),
            telefone=request.form.get("telefone", ""),
            endereco=request.form.get("endereco", ""),
            cpf=cpf,
            cnpj=cnpj,
            insc_estadual=insc_estadual if cnpj else None,
            tipo=int(request.form.get("tipo", 0)),
        )
        db.session.add(conta)
        db.session.commit()
        flash("Conta cadastrada!", "success")
        return redirect(url_for("contas.list"))
    return render_template("contas/form.html", conta=None, TIPO_CONTA=TIPO_CONTA)


@bp.route("/contas/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    conta = Conta.query.get(id)
    if not conta:
        flash("Código inexistente", "warning")
        return redirect(url_for("contas.list"))

    query = Conta.query.with_entities(Conta.id).order_by(Conta.id)
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

    orders = conta.orders.order_by(Order.data_pedido.desc()).all()

    if request.method == "POST":
        cpf = request.form.get("cpf", "").strip() or None
        cnpj = request.form.get("cnpj", "").strip() or None
        insc_estadual = request.form.get("insc_estadual", "").strip() or None
        if cpf and cnpj:
            flash("Preencha apenas CPF ou CNPJ, não ambos.", "warning")
            return render_template("contas/form.html", conta=conta, nav=nav, orders=orders, ORDER_STATUS=ORDER_STATUS, TIPO_CONTA=TIPO_CONTA)
        if cpf and not _cpf_valido(cpf):
            flash("CPF inválido.", "warning")
            return render_template("contas/form.html", conta=conta, nav=nav, orders=orders, ORDER_STATUS=ORDER_STATUS, TIPO_CONTA=TIPO_CONTA)
        if cnpj and not _cnpj_valido(cnpj):
            flash("CNPJ inválido.", "warning")
            return render_template("contas/form.html", conta=conta, nav=nav, orders=orders, ORDER_STATUS=ORDER_STATUS, TIPO_CONTA=TIPO_CONTA)
        conta.nome = request.form["nome"]
        conta.email = (request.form["email"] or None)
        conta.telefone = request.form.get("telefone", "")
        conta.endereco = request.form.get("endereco", "")
        conta.cpf = cpf
        conta.cnpj = cnpj
        conta.insc_estadual = insc_estadual if cnpj else None
        conta.tipo = int(request.form.get("tipo", 0))
        db.session.commit()
        flash("Conta atualizada!", "success")
        return redirect(url_for("contas.list"))

    return render_template("contas/form.html", conta=conta, nav=nav, orders=orders, ORDER_STATUS=ORDER_STATUS, TIPO_CONTA=TIPO_CONTA)


@bp.route("/contas/<int:id>/toggle")
def toggle(id):
    conta = Conta.query.get_or_404(id)
    conta.ativo = not conta.ativo
    db.session.commit()
    flash("Conta atualizada!", "success")
    return redirect(url_for("contas.edit", id=id))
