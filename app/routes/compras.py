from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.previsao import Previsao
from app.models.transacao import Transacao
from app.models.compra import Compra
from app.models.client import Conta
from app.models.rubrica import Rubrica
from app.models.ingredient import Ingredient
from app.models.compra_item import CompraItem
from app.models.movto import Movto
from app.constants import TIPO_PREVISAO, TIPO_RUBRICA, PREVISAO_STATUS, TIPO_TRANSACAO, COMPRA_STATUS
from app.models.forma_pagamento import FormaPagamento
from app.utils import LinhaTransacao

TIPO = "C"

bp = Blueprint("compras", __name__, url_prefix="/compras")


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
        Transacao.tipo == TIPO
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
        linhas = [l for l in linhas if l.vencimento < hoje and l.status not in (8, 9)]
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
    return render_template(
        "compras/list.html", linhas=linhas, total_saldo=total_saldo,
        filtro_status=filtro_status, filtro_venc=filtro_venc, hoje=hoje,
        TIPO_PREVISAO=TIPO_PREVISAO, TIPO_RUBRICA=TIPO_RUBRICA,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
        TIPO_TRANSACAO=TIPO_TRANSACAO,
    )


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        data = request.form.get("data") or date.today()
        conta_id = request.form.get("conta_id", type=int) or None
        rubrica_id = request.form.get("rubrica_id", type=int) or None
        fatura = request.form.get("fatura") or None
        historico = request.form.get("historico") or None
        cancelado = request.form.get("cancelado") or None

        insumo_ids = request.form.getlist("insumo_id[]")
        quantidades = request.form.getlist("quantidade[]")
        precos = request.form.getlist("preco[]")

        valor_total = 0.0
        for i in range(len(insumo_ids)):
            if not insumo_ids[i] or not insumo_ids[i].strip():
                continue
            qtd = float(quantidades[i]) if quantidades[i] and quantidades[i].strip() else 0
            prc = float(precos[i]) if precos[i] and precos[i].strip() else 0
            valor_total += qtd * prc

        compra = Compra(
            data=data, fornecedor_id=conta_id,
            valor=valor_total, historico=historico,
            forma_pagamento_id=request.form.get("forma_pagamento_id", type=int) or None,
            status=1,
        )
        db.session.add(compra)
        db.session.flush()

        transacao = Transacao(
            data=data, tipo=TIPO, conta_id=conta_id,
            rubrica_id=rubrica_id, fatura=fatura,
            valor=valor_total, cancelado=cancelado,
            historico=historico,
        )
        db.session.add(transacao)
        db.session.flush()
        compra.transacao_id = transacao.id

        for i in range(len(insumo_ids)):
            if not insumo_ids[i] or not insumo_ids[i].strip():
                continue
            qtd = float(quantidades[i]) if quantidades[i] and quantidades[i].strip() else 0
            prc = float(precos[i]) if precos[i] and precos[i].strip() else 0
            if qtd and prc:
                item = CompraItem(
                    compra_id=compra.id,
                    insumo_id=int(insumo_ids[i]),
                    quantidade=qtd, preco=prc,
                )
                db.session.add(item)

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
                vencimento=vencs[i], previsto=prev_val,
                realizado=real_val, variacao=var_val,
            )
            db.session.add(previsao)

        if prev_total > transacao.valor:
            db.session.rollback()
            flash(f"Total das parcelas ({prev_total:.2f}) excede o valor da compra ({float(transacao.valor):.2f})", "danger")
            contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
            rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
            insumos = Ingredient.query.order_by(Ingredient.nome).all()
            formas_pagamento = FormaPagamento.query.order_by(FormaPagamento.nome).all()
            return render_template(
                "compras/form.html",
                contas=contas, rubricas=rubricas, insumos=insumos,
                formas_pagamento=formas_pagamento, hoje=date.today(),
                COMPRA_STATUS=COMPRA_STATUS,
                submitted_data=None, submitted_previsoes=None,
                compra=None,
            )

        db.session.commit()
        flash("Compra cadastrada!", "success")
        return redirect(url_for("compras.list"))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    formas_pagamento = FormaPagamento.query.order_by(FormaPagamento.nome).all()
    return render_template(
        "compras/form.html", contas=contas, rubricas=rubricas,
        insumos=insumos, formas_pagamento=formas_pagamento,
        hoje=date.today(), COMPRA_STATUS=COMPRA_STATUS,
        submitted_data=None, submitted_previsoes=None,
        compra=None,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    transacao = Transacao.query.options(joinedload(Transacao.previsoes)).get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("compras.list"))

    compra = Compra.query.filter_by(transacao_id=transacao.id).first()
    if not compra:
        flash("Compra não encontrada", "warning")
        return redirect(url_for("compras.list"))

    query = Transacao.query.with_entities(Transacao.id).filter(Transacao.tipo == TIPO).order_by(Transacao.id)
    ids = [t.id for t in query.all()]
    try:
        current_idx = ids.index(id)
        nav = {
            "first_id": ids[0], "last_id": ids[-1],
            "prev_id": ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": ids[current_idx + 1] if current_idx < len(ids) - 1 else None,
        }
    except ValueError:
        nav = {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}

    if request.method == "POST":
        cancelado = request.form.get("cancelado") or None
        compra.data = request.form.get("data") or date.today()
        compra.fornecedor_id = request.form.get("conta_id", type=int) or None
        compra.historico = request.form.get("historico") or None
        compra.forma_pagamento_id = request.form.get("forma_pagamento_id", type=int) or None
        compra.data_recepcao = request.form.get("data_recepcao") or None

        transacao.data = compra.data
        transacao.conta_id = compra.fornecedor_id
        transacao.rubrica_id = request.form.get("rubrica_id", type=int) or None
        transacao.fatura = request.form.get("fatura") or None
        transacao.cancelado = cancelado
        transacao.historico = compra.historico

        insumo_ids = request.form.getlist("insumo_id[]")
        quantidades = request.form.getlist("quantidade[]")
        precos = request.form.getlist("preco[]")
        item_ids = request.form.getlist("item_id[]")
        item_removes = request.form.getlist("item_remover[]")

        valor_total = 0.0
        existing_items = {ci.id for ci in compra.items}
        submitted_items = set()

        for i in range(len(insumo_ids)):
            if not insumo_ids[i] or not insumo_ids[i].strip():
                continue
            qtd = float(quantidades[i]) if quantidades[i] and quantidades[i].strip() else 0
            prc = float(precos[i]) if precos[i] and precos[i].strip() else 0
            iid = int(item_ids[i]) if item_ids[i] and item_ids[i].strip() else None

            if item_removes[i] == "1" if i < len(item_removes) else False:
                if iid:
                    db.session.delete(CompraItem.query.get(iid))
                continue

            submitted_items.add(iid)
            if iid:
                ci = CompraItem.query.get(iid)
                if ci:
                    ci.insumo_id = int(insumo_ids[i])
                    ci.quantidade = qtd
                    ci.preco = prc
            else:
                ci = CompraItem(
                    compra_id=compra.id,
                    insumo_id=int(insumo_ids[i]),
                    quantidade=qtd, preco=prc,
                )
                db.session.add(ci)
            valor_total += qtd * prc

        for eid in (existing_items - submitted_items):
            db.session.delete(CompraItem.query.get(eid))

        compra.valor = valor_total
        transacao.valor = valor_total

        existing = {p.id for p in transacao.previsoes}
        submitted = set()

        pids = request.form.getlist("previsao_id[]")
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
            pid = int(pids[i]) if pids[i] and pids[i].strip() else None
            if removes[i] == "1" if i < len(removes) else False:
                if pid:
                    db.session.delete(Previsao.query.get(pid))
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
                    vencimento=vencs[i], previsto=prev_val,
                    realizado=real_val, variacao=var_val,
                )
                db.session.add(p)

        for pid in (existing - submitted):
            db.session.delete(Previsao.query.get(pid))

        if prev_total > transacao.valor:
            db.session.rollback()
            flash(f"Total das parcelas ({prev_total:.2f}) excede o valor da compra ({float(transacao.valor):.2f})", "danger")
        else:
            db.session.commit()
            flash("Compra atualizada!", "success")
            return redirect(url_for("compras.list"))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    formas_pagamento = FormaPagamento.query.order_by(FormaPagamento.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes]
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "compras/form.html", transacao=transacao, compra=compra,
        contas=contas, rubricas=rubricas, insumos=insumos,
        formas_pagamento=formas_pagamento,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Pagamento",
    )
