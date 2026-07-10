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
from app.constants import PREVISAO_STATUS, COMPRA_STATUS
from app.models.carteira import Carteira
from app.utils import CompraLinha
from app.fields import Field, build_field_context, Table


COMPRAS_MASTER_FIELDS = [
    Field(name='compra_id', label='Compra', width=8),
    Field(name='status_compra', label='Status', width=10, options=COMPRA_STATUS, filter_options=list(COMPRA_STATUS.values())),
    Field(name='carteira', label='FP', width=12, query='carteira'),
    Field(name='faturado', label='Faturado', width=10, filter=False),
    Field(name='fornecedor', label='Fornecedor', width=30, query='conta', pos=1),
    Field(name='fatura', label='Fatura', width=10),
    Field(name='valor', label='Valor', width=12, input='number', align='right', currency='brl'),
]

PREVISOES_DETAIL_FIELDS = [
    Field(name='id', label='Previsão', width=8),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='documento', label='Documento', width=10),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='status', label='Pagamento', width=10, options=PREVISAO_STATUS, filter_options=list(PREVISAO_STATUS.values())),
]

COMPRAS_TABLE = Table(
    fields=COMPRAS_MASTER_FIELDS,
    edit_endpoint='compras.edit',
    edit_id_field='compra_id',
    detail_fields=PREVISOES_DETAIL_FIELDS,
    detail_data='previsoes',
)

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
    compras = Compra.query.options(
        joinedload(Compra.transacao).joinedload(Transacao.previsoes)
    ).order_by(Compra.data.desc(), Compra.id.desc()).all()

    linhas = [CompraLinha(compra=c, transacao=c.transacao) for c in compras]

    if filtro_status != "todos":
        linhas = [l for l in linhas if any(
            p.status == int(filtro_status) for p in l.previsoes
        )]
    if filtro_venc == "em_atraso":
        linhas = [l for l in linhas if any(
            p.vencimento and p.vencimento < hoje and p.status not in (8, 9)
            for p in l.previsoes
        )]
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
        linhas = [l for l in linhas if any(
            p.vencimento in dias and p.status not in (0, 8, 9)
            for p in l.previsoes
        )]
    elif filtro_venc == "a_vencer":
        linhas = [l for l in linhas if any(
            p.vencimento and p.vencimento > hoje and p.status not in (0, 8, 9)
            for p in l.previsoes
        )]

    total_saldo = sum(sum(p.saldo for p in l.previsoes) for l in linhas)
    ctx = build_field_context(COMPRAS_MASTER_FIELDS)
    return render_template(
        "sys_compras/list.html", linhas=linhas, total_saldo=total_saldo,
        COMPRAS_TABLE=COMPRAS_TABLE, ctx=ctx,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
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
            carteira_id=request.form.get("carteira_id", type=int) or None,
            status=1,
        )
        db.session.add(compra)
        db.session.flush()

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

        db.session.commit()
        flash("Compra cadastrada!", "success")
        return redirect(url_for("compras.list"))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "sys_compras/form.html", contas=contas, rubricas=rubricas,
        insumos=insumos, carteiras=carteiras,
        hoje=date.today(), COMPRA_STATUS=COMPRA_STATUS,
        submitted_data=None, submitted_previsoes=None,
        compra=None,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    compra = Compra.query.options(joinedload(Compra.items)).get(id)
    if not compra:
        flash("Código inexistente", "warning")
        return redirect(url_for("compras.list"))

    transacao = Transacao.query.options(joinedload(Transacao.previsoes)).get(compra.transacao_id) if compra.transacao_id else None

    compra_ids = [c.id for c in Compra.query.order_by(Compra.data, Compra.id).all()]
    nav = {}
    try:
        current_idx = compra_ids.index(compra.id)
        nav = {
            "first_id": compra_ids[0], "last_id": compra_ids[-1],
            "prev_id": compra_ids[current_idx - 1] if current_idx > 0 else None,
            "next_id": compra_ids[current_idx + 1] if current_idx < len(compra_ids) - 1 else None,
        }
    except ValueError:
        nav = {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}

    if request.method == "POST":
        compra.data = request.form.get("data") or date.today()
        compra.fornecedor_id = request.form.get("conta_id", type=int) or None
        compra.historico = request.form.get("historico") or None
        compra.carteira_id = request.form.get("carteira_id", type=int) or None
        compra.data_recepcao = request.form.get("data_recepcao") or None

        if transacao and not compra.movto_id:
            transacao.data = compra.data
            transacao.conta_id = compra.fornecedor_id
            transacao.rubrica_id = request.form.get("rubrica_id", type=int) or None
            transacao.fatura = request.form.get("fatura") or None
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
        if transacao:
            transacao.valor = valor_total

        if transacao:
            existing = {p.id for p in transacao.previsoes}
            submitted = set()
            deleted = set()

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
                        vencimento=vencs[i], previsto=prev_val,
                        realizado=real_val, variacao=var_val,
                    )
                    db.session.add(p)

            for pid in (existing - submitted - deleted):
                p = Previsao.query.get(pid)
                if p and p.movtos:
                    flash(f"Parcela #{p.id} possui movimentos, exclua-os primeiro", "danger")
                elif p:
                    db.session.delete(p)

            transacao.total_previsto = prev_total

            if prev_total > float(transacao.valor):
                db.session.rollback()
                flash(f"Total das parcelas ({prev_total:.2f}) excede o valor da compra ({float(transacao.valor):.2f})", "danger")
            else:
                db.session.commit()
                flash("Compra atualizada!", "success")
                redirect_after = request.form.get("redirect_after")
                if redirect_after:
                    return redirect(redirect_after)
                return redirect(url_for("compras.edit", id=compra.id))
        else:
            db.session.commit()
            flash("Compra atualizada!", "success")
            redirect_after = request.form.get("redirect_after")
            if redirect_after:
                return redirect(redirect_after)
            return redirect(url_for("compras.edit", id=compra.id))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    rubricas = Rubrica.query.filter_by(ativa=True, tipo=2).order_by(Rubrica.ordem, Rubrica.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes] if transacao else []
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "sys_compras/form.html", transacao=transacao, compra=compra,
        contas=contas, rubricas=rubricas, insumos=insumos,
        carteiras=carteiras,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Pagamento",
    )
