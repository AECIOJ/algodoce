from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.previsao import Previsao
from app.models.transacao import Transacao
from app.models.client import Conta
from app.models.rubrica import Rubrica
from app.models.movto import Movto
from app.models.compra import Compra
from app.models.order import Order
from app.constants import PREVISAO_STATUS
from app.utils import LinhaTransacao
from app.fields import Field, build_field_context


CONTAS_A_PAGAR_FIELDS = [
    Field(name='transacao_id', label='Transação', width=8, card_path='transacao.id'),
    Field(name='compra_id', label='Compra', width=6),
    Field(name='status', label='Status', width=10, options=PREVISAO_STATUS, filter_options=list(PREVISAO_STATUS.values())),
    Field(name='fornecedor', label='Conta', width=15, query='conta'),
    Field(name='fatura', label='Fatura', width=10),
    Field(name='valor', label='Valor', width=10, input='number', align='right', currency='brl'),
    Field(name='documento', label='Documento', width=10),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='id', label='Previsão', width=8),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
]

TIPO = ("P", "C")

bp = Blueprint("contas_a_pagar", __name__, url_prefix="/contas-a-pagar")


def _build_submitted():
    data = {
        "data": request.form.get("data"),
        "conta_id": request.form.get("conta_id"),
        "rubrica_id": request.form.get("rubrica_id"),
        "fatura": request.form.get("fatura"),
        "valor": request.form.get("valor"),
        "cancelado": request.form.get("cancelado"),
        "historico": request.form.get("historico"),
    }
    ids = request.form.getlist("previsao_id[]")
    docs = request.form.getlist("previsao_documento[]")
    vencs = request.form.getlist("previsao_vencimento[]")
    prevs = request.form.getlist("previsao_previsto[]")
    reals = request.form.getlist("previsao_realizado[]")
    vars_ = request.form.getlist("previsao_variacao[]")
    previsoes = []
    for i in range(len(vencs)):
        if not vencs[i] or not vencs[i].strip():
            continue
        previsoes.append(dict(
            id=int(ids[i]) if ids[i] and ids[i].strip() else None,
            documento=docs[i] if docs[i] and docs[i].strip() else None,
            vencimento=vencs[i],
            previsto=float(prevs[i]) if prevs[i] and prevs[i].strip() else 0,
            realizado=float(reals[i]) if reals[i] and reals[i].strip() else None,
            variacao=float(vars_[i]) if vars_[i] and vars_[i].strip() else 0,
        ))
    return data, previsoes


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    hoje = date.today()
    filtro_status = request.args.get("status", "todos")
    filtro_venc = request.args.get("vencimento", "todos")
    transacoes = Transacao.query.options(
        joinedload(Transacao.previsoes)
    ).filter(
        Transacao.tipo.in_(TIPO)
    ).order_by(Transacao.data, Transacao.id).all()

    linhas = []
    for t in transacoes:
        if t.previsoes:
            for p in t.previsoes:
                linhas.append(LinhaTransacao(t, p))
        else:
            linhas.append(LinhaTransacao(t))

    if filtro_status != "todos":
        linhas = [l for l in linhas if l.status == int(filtro_status)]
    if filtro_venc == "em_atraso":
        linhas = [l for l in linhas if l.vencimento < hoje and l.status not in (0, 8, 9)]
    elif filtro_venc == "hoje":
        w = hoje.weekday()
        if w == 5:
            dias = [hoje, hoje + timedelta(days=1), hoje + timedelta(days=2)]
        elif w == 6:
            dias = [hoje, hoje - timedelta(days=1), hoje + timedelta(days=1)]
        elif w == 0:
            dias = [hoje, hoje - timedelta(days=1), hoje - timedelta(days=2)]
        else:
            dias = [hoje]
        linhas = [l for l in linhas if l.vencimento in dias and l.status not in (0, 8, 9)]
    elif filtro_venc == "a_vencer":
        linhas = [l for l in linhas if l.vencimento > hoje and l.status not in (0, 8, 9)]

    total_saldo = sum(l.saldo for l in linhas)
    ctx = build_field_context(CONTAS_A_PAGAR_FIELDS)
    return render_template(
        "contas_a_pagar/list.html", previsoes=linhas, total_saldo=total_saldo,
        fields=CONTAS_A_PAGAR_FIELDS, ctx=ctx,
        PREVISAO_STATUS=PREVISAO_STATUS,
    )


@bp.route("/<int:id>/detalhes")
def detail(id):
    transacao = Transacao.query.options(joinedload(Transacao.previsoes)).get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("contas_a_pagar.list"))
    return render_template(
        "contas_a_pagar/detalhes.html", t=transacao,
        hoje=date.today(), PREVISAO_STATUS=PREVISAO_STATUS,
    )


@bp.route("/novo", methods=["GET", "POST"])
def new():
    compra_id = request.args.get("compra_id", type=int) or request.form.get("compra_id", type=int)
    compra = Compra.query.get(compra_id) if compra_id else None
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "GET":
        if compra and compra.transacao_id:
            return redirect(url_for("contas_a_pagar.edit", id=compra.transacao_id))
        contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
        rubricas = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.ordem, Rubrica.nome).all()
        submitted_data = None
        if compra:
            submitted_data = {
                "data": str(compra.data or date.today()),
                "conta_id": str(compra.fornecedor_id),
                "rubrica_id": "",
                "fatura": f"C#{compra.id}",
                "valor": str(compra.valor or 0),
                "historico": compra.historico or "",
            }
        return render_template(
            "contas_a_pagar/form.html",
            contas=contas, rubricas=rubricas, hoje=date.today(),
            submitted_data=submitted_data, submitted_previsoes=None,
            prazo_inicial=prazo_inicial,
            locked=False, transacao=None, nav={}, movimentos=[],
            PREVISAO_STATUS=PREVISAO_STATUS, tipo_nome="Pagamento",
        )
    if request.method == "POST":
        submitted_data, submitted_previsoes = _build_submitted()

        cancelado = request.form.get("cancelado") or None
        transacao = Transacao(
            data=request.form.get("data") or date.today(),
            tipo='P',
            conta_id=request.form.get("conta_id", type=int) or None,
            rubrica_id=request.form.get("rubrica_id", type=int) or None,
            fatura=request.form.get("fatura") or None,
            valor=float(request.form.get("valor", 0)),
            cancelado=cancelado,
            historico=request.form.get("historico") or None,
        )
        db.session.add(transacao)
        db.session.flush()

        docs = request.form.getlist("previsao_documento[]")
        vencs = request.form.getlist("previsao_vencimento[]")
        prevs = request.form.getlist("previsao_previsto[]")
        reals = request.form.getlist("previsao_realizado[]")
        vars_ = request.form.getlist("previsao_variacao[]")

        prev_total = 0
        for i in range(len(vencs)):
            if not vencs[i]:
                continue
            prev_val = float(prevs[i]) if prevs[i] and prevs[i].strip() else 0
            prev_total += prev_val
            real_val = float(reals[i]) if reals[i] and reals[i].strip() else None
            var_val = float(vars_[i]) if vars_[i] and vars_[i].strip() else 0
            previsao = Previsao(
                transacao_id=transacao.id,
                documento=docs[i] if docs[i] and docs[i].strip() else None,
                vencimento=vencs[i],
                previsto=prev_val,
                realizado=real_val,
                variacao=var_val,
            )
            db.session.add(previsao)

        transacao.total_previsto = prev_total

        if abs(prev_total - transacao.valor) > 0.005:
            db.session.rollback()
            flash(f"Total das parcelas ({prev_total:.2f}) difere do valor da fatura ({float(transacao.valor):.2f})", "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            rubricas = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.ordem, Rubrica.nome).all()
            return render_template(
                "contas_a_pagar/form.html",
                contas=contas, rubricas=rubricas, hoje=date.today(),
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                prazo_inicial=prazo_inicial,
                locked=False, transacao=None, nav={}, movimentos=[],
                PREVISAO_STATUS=PREVISAO_STATUS, tipo_nome="Pagamento",
            )

        if compra and abs(float(transacao.valor) - float(compra.valor or 0)) > 0.005:
            db.session.rollback()
            flash(f"Valor da transação ({transacao.valor:.2f}) difere do valor da compra ({float(compra.valor or 0):.2f})", "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            rubricas = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.ordem, Rubrica.nome).all()
            return render_template(
                "contas_a_pagar/form.html",
                contas=contas, rubricas=rubricas, hoje=date.today(),
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                prazo_inicial=prazo_inicial,
                locked=False, transacao=None, nav={}, movimentos=[],
                PREVISAO_STATUS=PREVISAO_STATUS, tipo_nome="Pagamento",
            )

        if compra and not compra.transacao_id:
            compra.transacao_id = transacao.id
            db.session.commit()
        else:
            db.session.commit()
        flash("Conta cadastrada!", "success")
        return redirect(url_for("contas_a_pagar.list"))


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    transacao = Transacao.query.get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("contas_a_pagar.list"))

    query = Transacao.query.with_entities(Transacao.id).filter(Transacao.tipo.in_(TIPO)).order_by(Transacao.id)
    ids = [t.id for t in query.all()]
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

    locked = bool(Compra.query.filter_by(transacao_id=transacao.id).first())
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "POST":
        submitted_data, submitted_previsoes = _build_submitted()

        if not locked:
            cancelado = request.form.get("cancelado") or None
            transacao.data = request.form.get("data") or date.today()
            transacao.conta_id = request.form.get("conta_id", type=int) or None
            transacao.rubrica_id = request.form.get("rubrica_id", type=int) or None
            transacao.fatura = request.form.get("fatura") or None
            transacao.valor = float(request.form.get("valor", 0))
            transacao.cancelado = cancelado
            transacao.historico = request.form.get("historico") or None

        existing = {p.id for p in transacao.previsoes}
        submitted = set()
        deleted = set()

        ids = request.form.getlist("previsao_id[]")
        docs = request.form.getlist("previsao_documento[]")
        vencs = request.form.getlist("previsao_vencimento[]")
        prevs = request.form.getlist("previsao_previsto[]")
        reals = request.form.getlist("previsao_realizado[]")
        vars_ = request.form.getlist("previsao_variacao[]")
        removes = request.form.getlist("previsao_remover[]")

        prev_total = 0
        for i in range(len(vencs)):
            if not vencs[i] or not vencs[i].strip():
                continue
            pid = int(ids[i]) if ids[i] and ids[i].strip() else None
            if removes[i] == "1" if i < len(removes) else False:
                if pid:
                    p = Previsao.query.get(pid)
                    if p and p.movtos:
                        flash(f"Parcela #{p.id} possui movimentos, exclua-os primeiro", "danger")
                    elif p:
                        db.session.delete(p)
                        deleted.add(pid)
                continue
            submitted.add(pid)
            prev_val = float(prevs[i]) if prevs[i] and prevs[i].strip() else 0
            prev_total += prev_val
            real_val = float(reals[i]) if reals[i] and reals[i].strip() else None
            var_val = float(vars_[i]) if vars_[i] and vars_[i].strip() else 0
            if pid:
                p = Previsao.query.get(pid)
                if p:
                    p.documento = docs[i] if docs[i].strip() else None
                    p.vencimento = vencs[i]
                    p.previsto = prev_val
                    p.realizado = real_val
                    p.variacao = var_val
            else:
                p = Previsao(
                    transacao_id=transacao.id,
                    documento=docs[i] if docs[i].strip() else None,
                    vencimento=vencs[i],
                    previsto=prev_val,
                    realizado=real_val,
                    variacao=var_val,
                )
                db.session.add(p)

        for pid in (existing - submitted - deleted):
            p = Previsao.query.get(pid)
            if p and p.movtos:
                flash(f"Parcela #{p.id} possui movimentos, exclua-os primeiro", "danger")
            elif p:
                db.session.delete(p)

        transacao.total_previsto = prev_total

        compra = transacao.compra
        errors = []

        if compra and abs(float(transacao.valor) - float(compra.valor or 0)) > 0.005:
            errors.append(f"Valor da transação ({transacao.valor:.2f}) difere do valor da compra ({float(compra.valor or 0):.2f})")

        if errors:
            db.session.rollback()
            for err in errors:
                flash(err, "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            rubricas = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.ordem, Rubrica.nome).all()
            previsao_ids = [p.id for p in transacao.previsoes]
            movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
            return render_template(
                "contas_a_pagar/form.html", transacao=transacao,
                contas=contas, rubricas=rubricas,
                PREVISAO_STATUS=PREVISAO_STATUS,
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes, nav=nav,
                movimentos=movimentos, tipo_nome="Pagamento", locked=locked,
                prazo_inicial=prazo_inicial,
            )
        else:
            db.session.commit()
            flash("Conta atualizada!", "success")
            return redirect(url_for("contas_a_pagar.list"))

    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True).order_by(Rubrica.ordem, Rubrica.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes]
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "contas_a_pagar/form.html", transacao=transacao,
        contas=contas, rubricas=rubricas,
        PREVISAO_STATUS=PREVISAO_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Pagamento", locked=locked,
        prazo_inicial=prazo_inicial,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def excluir(id):
    transacao = Transacao.query.get(id)
    if not transacao:
        flash("Registro inexistente", "warning")
        return redirect(url_for("contas_a_pagar.list"))

    if transacao.previsoes:
        flash("Exclua as parcelas antes de excluir a transação", "danger")
        return redirect(url_for("contas_a_pagar.list"))

    compra = Compra.query.filter_by(transacao_id=transacao.id).first()
    compra_id = compra.id if compra else None
    order = Order.query.filter_by(transacao_id=transacao.id).first()

    if compra:
        compra.transacao_id = None
    if order:
        order.transacao_id = None

    db.session.delete(transacao)
    db.session.commit()
    flash("Conta excluída!", "success")

    if compra_id:
        return redirect(url_for("compras.edit", id=compra_id))
    return redirect(url_for("contas_a_pagar.list"))
