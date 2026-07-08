from datetime import date, datetime
from types import SimpleNamespace
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.extensions import db
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.models.client import Conta
from app.models.previsao import Previsao
from app.models.transacao import Transacao
from app.models.compra import Compra
from app.models.order import Order
from app.models.rubrica import Rubrica
from app.constants import TIPO_RECURSO, TIPO_RUBRICA, PREVISAO_STATUS
from app.fields import Field, build_field_context
from decimal import Decimal

bp = Blueprint("movimentos", __name__, url_prefix="/movimentos")


MOVIMENTOS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='data', label='Data', width=10, input='date'),
    Field(name='recurso', label='Recurso', width=15, query='recurso'),
    Field(name='conta', label='Conta', width=15, query='conta', card_pos=1, card_path='conta.nome'),
    Field(name='previsao', label='Previsão', width=10, filter=False),
    Field(name='documento', label='Documento', width=10),
    Field(name='valor', label='Valor', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='rubrica', label='Rubrica', width=15, query='rubrica'),
    Field(name='historico', label='Histórico', width=30),
]


@bp.before_request
@login_required
def protect():
    pass


def _movto_tipo(tipo):
    return "Recebimento" if tipo == "E" else "Pagamento"


def _movto_tipo_plural(tipo):
    return "Recebimentos" if tipo == "E" else "Pagamentos"


def _list(tipo):
    filtro_recurso = request.args.get("recurso", "todos")
    query = Movto.query.filter(Movto.tipo == tipo)
    if filtro_recurso != "todos":
        query = query.filter(Movto.recurso_id == int(filtro_recurso))
    movtos = query.order_by(Movto.data.desc(), Movto.id.desc()).all()
    ctx = build_field_context(MOVIMENTOS_FIELDS)
    return render_template(
        "movimentos/list.html",
        movtos=movtos, fields=MOVIMENTOS_FIELDS, ctx=ctx,
        tipo=tipo, tipo_nome=_movto_tipo(tipo),
        tipo_nome_plural=_movto_tipo_plural(tipo),
    )


def _new(tipo, prefill=None, from_order=False, compra=None):
    recursos = Recurso.query.order_by(Recurso.nome).all()
    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    if tipo == "E":
        rubricas = Rubrica.query.filter_by(ativa=True, tipo=1).order_by(Rubrica.ordem, Rubrica.nome).all()
    else:
        rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
    return render_template(
        "movimentos/form.html",
        movto=None, recursos=recursos, contas=contas, rubricas=rubricas,
        tipo=tipo, tipo_nome=_movto_tipo(tipo),
        tipo_nome_plural=_movto_tipo_plural(tipo),
        TIPO_RECURSO=TIPO_RECURSO, PREVISAO_STATUS=PREVISAO_STATUS,
        prefill=prefill, from_order=from_order, compra=compra,
    )


def _edit(id):
    movto = Movto.query.get(id)
    if not movto:
        flash("Registro inexistente", "warning")
        return None
    return movto


def _sincronizar_previsao(movto, operacao):
    if not movto.previsao_id:
        return
    p = Previsao.query.get(movto.previsao_id)
    if not p:
        return
    sinal = -1 if operacao == 'excluir' else 1
    if movto.variacao:
        p.variacao = (p.variacao or 0) + Decimal(str(movto.variacao)) * sinal
    if movto.sincronizar:
        ajuste = Decimal(str(movto.valor)) * sinal
        p.realizado = max(0, (p.realizado or 0) + ajuste)


def _create_or_update(movto, tipo, compra=None):
    data = request.form.get("data")
    recurso_id = request.form.get("recurso_id", type=int)
    conta_id = request.form.get("conta_id", type=int) or None
    previsao_id = request.form.get("previsao_id", type=int) or None
    documento = request.form.get("documento") or None
    valor = float(request.form.get("valor", 0))
    rubrica_id = request.form.get("rubrica_id", type=int) or None
    historico = request.form.get("historico") or None
    acao = request.form.get("acao", "")

    if not data or not recurso_id or not valor:
        flash("Preencha data, recurso e valor", "danger")
        return False

    if previsao_id:
        p = Previsao.query.get(previsao_id)
        if p and p.transacao and abs(float(p.transacao.total_previsto or 0) - float(p.transacao.valor)) > 0.005:
            flash("Transação está em estado 'Editando' — reajuste o valor antes de lançar movimentos", "danger")
            return False

    if movto and movto.id:
        if not historico:
            old_variacao = float(movto.variacao or 0)
            if old_variacao != 0:
                historico = 'Haver na data' if old_variacao < 0 else 'Acréscimos na data'
            else:
                historico = 'Pago na data' if tipo == 'S' else 'Recebido na data'

        old_valor = float(movto.valor)

        if abs(valor - old_valor) < 0.01:
            movto.data = data
            movto.recurso_id = recurso_id
            movto.tipo = tipo
            movto.conta_id = conta_id
            movto.previsao_id = previsao_id
            movto.documento = documento
            movto.rubrica_id = rubrica_id
            movto.historico = historico
            db.session.commit()
            return True

        _sincronizar_previsao(movto, 'excluir')
        movto.data = data
        movto.recurso_id = recurso_id
        movto.tipo = tipo
        movto.conta_id = conta_id
        movto.previsao_id = previsao_id
        movto.documento = documento
        movto.valor = valor
        movto.variacao = 0
        movto.sincronizar = True
        movto.rubrica_id = rubrica_id
        movto.historico = historico
        _sincronizar_previsao(movto, 'criar')
        db.session.commit()
        return True

    variacao = 0
    sincronizar = True

    if acao == "desconto":
        p = Previsao.query.get(previsao_id)
        if p:
            saldo = p.saldo
            diferenca = saldo - valor
            variacao = -diferenca

    elif acao == "acrescimos":
        rubrica_acrescimos_id = request.form.get("rubrica_acrescimos_id", type=int)
        if not rubrica_acrescimos_id:
            flash("Selecione a rubrica para acréscimos", "danger")
            return False
        p = Previsao.query.get(previsao_id)
        if p:
            saldo = p.saldo
            diferenca = valor - saldo

        historico_sec = historico or 'Acréscimos na data'
        movto_acrescimos = Movto(
            data=data, recurso_id=recurso_id, tipo=tipo,
            conta_id=conta_id, previsao_id=previsao_id,
            documento=documento, valor=diferenca,
            variacao=diferenca, sincronizar=False,
            rubrica_id=rubrica_acrescimos_id,
            historico=historico_sec,
        )
        valor = saldo

    if not historico:
        if acao == "desconto":
            historico = 'Haver na data'
        else:
            historico = 'Pago na data' if tipo == 'S' else 'Recebido na data'

    movto = Movto(
        data=data, recurso_id=recurso_id, tipo=tipo,
        conta_id=conta_id, previsao_id=previsao_id,
        documento=documento, valor=valor,
        variacao=variacao, sincronizar=sincronizar,
        rubrica_id=rubrica_id, historico=historico,
    )
    db.session.add(movto)

    if acao == "acrescimos":
        db.session.add(movto_acrescimos)
        db.session.flush()
        _sincronizar_previsao(movto, 'criar')
        _sincronizar_previsao(movto_acrescimos, 'criar')
    else:
        db.session.flush()
        _sincronizar_previsao(movto, 'criar')
    if compra and not compra.movto_id:
        compra.movto_id = movto.id
    db.session.commit()
    return True


@bp.route("/recebimentos")
def recebimentos_list():
    return _list("E")


@bp.route("/recebimentos/novo", methods=["GET", "POST"])
def recebimentos_new():
    if request.method == "POST":
        if _create_or_update(None, "E"):
            flash("Recebimento registrado!", "success")
            return redirect(url_for("movimentos.recebimentos_list"))
    prefill = None
    order_id = request.args.get("order_id", type=int)
    if order_id:
        from app.models.order import Order
        order = Order.query.get(order_id)
        if order:
            total = float(order.total or 0)
            prefill = SimpleNamespace(
                conta_id=order.client_id,
                documento=f"P#{order.id}",
                valor=total,
                historico="Recebimento de Vendas na data",
            )
    return _new("E", prefill=prefill, from_order=bool(order_id))


@bp.route("/recebimentos/<int:id>/editar", methods=["GET", "POST"])
def recebimentos_edit(id):
    movto = _edit(id)
    if movto is None:
        return redirect(url_for("movimentos.recebimentos_list"))

    recursos = Recurso.query.order_by(Recurso.nome).all()
    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=1).order_by(Rubrica.ordem, Rubrica.nome).all()

    query = Movto.query.with_entities(Movto.id).filter(Movto.tipo == "E").order_by(Movto.data.desc(), Movto.id.desc())
    ids = [m.id for m in query.all()]
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

    if request.method == "POST":
        if _create_or_update(movto, "E"):
            flash("Recebimento atualizado!", "success")
            return redirect(url_for("movimentos.recebimentos_list"))

    return render_template(
        "movimentos/form.html",
        movto=movto, recursos=recursos, contas=contas, rubricas=rubricas,
        nav=nav,
        tipo="E", tipo_nome=_movto_tipo("E"),
        tipo_nome_plural=_movto_tipo_plural("E"),
        TIPO_RECURSO=TIPO_RECURSO, PREVISAO_STATUS=PREVISAO_STATUS,
    )


@bp.route("/pagamentos")
def pagamentos_list():
    return _list("S")


@bp.route("/pagamentos/novo", methods=["GET", "POST"])
def pagamentos_new():
    compra_id = request.args.get("compra_id", type=int)
    compra = Compra.query.get(compra_id) if compra_id else None
    rubrica_id = request.args.get("rubrica_id", type=int)
    if request.method == "POST":
        if _create_or_update(None, "S", compra=compra):
            flash("Pagamento registrado!", "success")
            return redirect(url_for("movimentos.pagamentos_list"))
    prefill = None
    if compra and not compra.movto_id:
        prefill = {
            "data": str(compra.data or date.today()),
            "conta_id": compra.fornecedor_id,
            "documento": f"C#{compra.id}",
            "rubrica_id": rubrica_id,
            "valor": str(compra.valor or 0),
            "historico": f"Pagamento na data ref. Compra (#{compra.id}) e Fatura (#C{compra.id})",
        }
    return _new("S", prefill=prefill, compra=compra)


@bp.route("/pagamentos/<int:id>/editar", methods=["GET", "POST"])
def pagamentos_edit(id):
    movto = _edit(id)
    if movto is None:
        return redirect(url_for("movimentos.pagamentos_list"))

    recursos = Recurso.query.order_by(Recurso.nome).all()
    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()

    query = Movto.query.with_entities(Movto.id).filter(Movto.tipo == "S").order_by(Movto.data.desc(), Movto.id.desc())
    ids = [m.id for m in query.all()]
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

    if request.method == "POST":
        if _create_or_update(movto, "S"):
            flash("Pagamento atualizado!", "success")
            return redirect(url_for("movimentos.pagamentos_list"))

    return render_template(
        "movimentos/form.html",
        movto=movto, recursos=recursos, contas=contas, rubricas=rubricas,
        nav=nav,
        tipo="S", tipo_nome=_movto_tipo("S"),
        tipo_nome_plural=_movto_tipo_plural("S"),
        TIPO_RECURSO=TIPO_RECURSO, PREVISAO_STATUS=PREVISAO_STATUS,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    movto = Movto.query.get(id)
    if not movto:
        flash("Registro inexistente", "warning")
        return redirect(url_for("movimentos.recebimentos_list"))
    tipo = movto.tipo
    compra = Compra.query.filter_by(movto_id=movto.id).first()
    order = Order.query.filter_by(movto_id=movto.id).first()
    if compra:
        compra.movto_id = None
    if order:
        order.movto_id = None
    _sincronizar_previsao(movto, 'excluir')
    db.session.delete(movto)
    db.session.commit()
    flash(f"{_movto_tipo(tipo)} excluído!", "success")
    if compra:
        return redirect(url_for("compras.edit", id=compra.id))
    if order:
        return redirect(url_for("orders.edit", id=order.id))
    if tipo == "E":
        return redirect(url_for("movimentos.recebimentos_list"))
    return redirect(url_for("movimentos.pagamentos_list"))


@bp.route("/api/previsoes")
def api_previsoes():
    conta_id = request.args.get("conta_id", type=int)
    tipo = request.args.get("tipo", "E")
    transacao_tipo = "R" if tipo == "E" else "P"
    query = Previsao.query.join(Transacao).filter(
        Transacao.tipo == transacao_tipo,
    )
    if conta_id:
        query = query.filter(Transacao.conta_id == conta_id)
    query = query.filter(
        db.or_(
            Previsao.realizado.is_(None),
            Previsao.realizado < Previsao.previsto + db.func.coalesce(Previsao.variacao, 0),
        )
    )
    previsoes = query.order_by(Previsao.vencimento).all()
    return jsonify([{
        "id": p.id,
        "documento": p.documento or "",
        "vencimento": p.vencimento.isoformat(),
        "previsto": float(p.previsto),
        "realizado": float(p.realizado or 0),
        "saldo": p.saldo,
        "transacao_id": p.transacao_id,
        "conta_nome": p.transacao.conta.nome if p.transacao.conta else "",
        "fatura": p.transacao.fatura or "",
        "rubrica_id": p.transacao.rubrica_id,
    } for p in previsoes])
