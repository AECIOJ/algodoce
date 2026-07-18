from datetime import date, timedelta
from io import BytesIO
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.previsao import Previsao
from app.models.transacao import Transacao
from app.models.compra import Compra
from app.models.client import Conta
from app.models.ingredient import Ingredient
from app.models.compra_item import CompraItem
from app.models.movto import Movto
from app.constants import PREVISAO_STATUS, COMPRA_STATUS
from app.models.carteira import Carteira
from app.filters import resolve_filters, apply_select_filter, apply_date_filter, apply_text_filter, apply_number_filter, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT
from app.utils import LinhaTransacao
from app.table import Field, build_field_context, Table
from app.pdf import gerar_pdf_relatorio
from app.models.compra_historico import CompraHistorico


COMPRAS_FIELDS = [
    Field(name='compra_id', label='Compra', width=8),
    Field(name='status_compra', label='Status', width=10, options=COMPRA_STATUS, filter_options=COMPRA_STATUS),
    Field(name='carteira', label='FP', width=12, query='carteira'),
    Field(name='fornecedor', label='Fornecedor', width=30, query='conta', pos=1),
    Field(name='fatura', label='Fatura', width=10),
    Field(name='valor', label='Valor', width=12, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='id', label='Previsão', width=8),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='documento', label='Documento', width=10),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='status', label='Pagamento', width=10, options=PREVISAO_STATUS, filter_options=PREVISAO_STATUS),
]

COMPRAS_TABLE = Table(
    fields=COMPRAS_FIELDS,
    fields_master=[1,2,3,4,5,6],
    fields_detail=[7,8,9,10,11,12,13,14],
    master_key='compra_id',
    edit_endpoint='compras.edit',
    edit_id_field='compra_id',
    send_endpoint='compras.print_compra',
)

COMPRAS_FILTERS = {
    'compra_id':    MODE_NUMBER,
    'status_compra': {**MODE_SELECT, 'options': COMPRA_STATUS},
    'carteira':     {**MODE_SELECT, 'filter_path': 'carteira'},
    'fornecedor':   {**MODE_SELECT, 'filter_path': 'fornecedor'},
    'fatura':       MODE_TEXT,
    'valor':        MODE_NUMBER,
    'id':           MODE_NUMBER,
    'vencimento':   MODE_DATE,
    'documento':    MODE_TEXT,
    'previsto':     MODE_NUMBER,
    'realizado':    MODE_NUMBER,
    'variacao':     MODE_NUMBER,
    'saldo':        MODE_NUMBER,
    'status':       {**MODE_SELECT, 'options': PREVISAO_STATUS},
}

TIPO = "C"

bp = Blueprint("compras", __name__, url_prefix="/compras")


def _calc_compra_status(compra):
    return compra.calc_status()


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    hoje = date.today()
    active = resolve_filters(COMPRAS_FILTERS, request.args)
    compras = Compra.query.options(
        joinedload(Compra.transacao).joinedload(Transacao.previsoes)
    ).order_by(Compra.data.desc(), Compra.id.desc()).all()

    linhas = []
    for c in compras:
        t = c.transacao
        if t and t.previsoes:
            for p in t.previsoes:
                linhas.append(LinhaTransacao(t, p, c))
        else:
            linhas.append(LinhaTransacao(t, compra=c))

    linhas = apply_date_filter(linhas, 'vencimento', active.get('vencimento'))
    linhas = apply_select_filter(linhas, 'status', active.get('status'), PREVISAO_STATUS)
    linhas = apply_select_filter(linhas, 'status_compra', active.get('status_compra'), COMPRA_STATUS)
    linhas = apply_select_filter(linhas, 'carteira', active.get('carteira'), {c.nome for c in Carteira.query.all()})
    linhas = apply_select_filter(linhas, 'fornecedor', active.get('fornecedor'), {c.nome for c in Conta.query.all()})
    linhas = apply_text_filter(linhas, 'fatura', active.get('fatura'))
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'documento', active.get('documento'))
    linhas = apply_number_filter(linhas, 'valor', active.get('valor'))
    linhas = apply_number_filter(linhas, 'previsto', active.get('previsto'))
    linhas = apply_number_filter(linhas, 'realizado', active.get('realizado'))
    linhas = apply_number_filter(linhas, 'variacao', active.get('variacao'))
    linhas = apply_number_filter(linhas, 'saldo', active.get('saldo'))

    total_saldo = sum(l.saldo for l in linhas)
    ctx = build_field_context(COMPRAS_TABLE.master_fields, filters_config=COMPRAS_FILTERS)
    return render_template(
        "sys_compras/list.html", linhas=linhas, total_saldo=total_saldo,
        COMPRAS_TABLE=COMPRAS_TABLE, ctx=ctx,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
        active_filters=active, FILTERS=COMPRAS_FILTERS,
    )


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        data = request.form.get("data") or date.today()
        conta_id = request.form.get("conta_id", type=int) or None
        fatura = request.form.get("fatura") or None
        historico = request.form.get("historico") or None

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
            status=0,
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

        evento_acoes = request.form.getlist("evento_acao[]")
        evento_datas = request.form.getlist("evento_data[]")
        evento_responsaveis = request.form.getlist("evento_responsavel[]")
        evento_motivos = request.form.getlist("evento_motivo[]")
        _ev_created = False
        for i, acao in enumerate(evento_acoes):
            acao = acao.strip()
            if not acao:
                continue
            ev_data = evento_datas[i].strip() if i < len(evento_datas) and evento_datas[i] else data
            ev_resp = evento_responsaveis[i].strip() if i < len(evento_responsaveis) else None
            ev_mot = evento_motivos[i].strip() if i < len(evento_motivos) else None
            evento = CompraHistorico(
                compra_id=compra.id,
                status=int(acao),
                data=ev_data,
                usuario=current_user.username if current_user.is_authenticated else None,
                responsavel=ev_resp or None,
                motivo=ev_mot or None,
            )
            db.session.add(evento)
            _ev_created = True

        db.session.commit()
        if _ev_created:
            compra.status = _calc_compra_status(compra)
            db.session.commit()
        flash("Compra cadastrada!", "success")
        return redirect(url_for("compras.list"))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "sys_compras/form.html", contas=contas,
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

        if transacao and not compra.movto_id:
            transacao.data = compra.data
            transacao.conta_id = compra.fornecedor_id
            transacao.operacao_id = request.form.get("operacao_id", type=int) or None
            transacao.fatura = request.form.get("fatura") or None
            transacao.historico = compra.historico

        evento_acoes = request.form.getlist("evento_acao[]")
        evento_datas = request.form.getlist("evento_data[]")
        evento_responsaveis = request.form.getlist("evento_responsavel[]")
        evento_motivos = request.form.getlist("evento_motivo[]")
        _ev_created = False
        for i, acao in enumerate(evento_acoes):
            acao = acao.strip()
            if not acao:
                continue
            ev_data = evento_datas[i].strip() if i < len(evento_datas) and evento_datas[i] else compra.data
            ev_resp = evento_responsaveis[i].strip() if i < len(evento_responsaveis) else None
            ev_mot = evento_motivos[i].strip() if i < len(evento_motivos) else None
            evento = CompraHistorico(
                compra_id=compra.id,
                status=int(acao),
                data=ev_data,
                usuario=current_user.username if current_user.is_authenticated else None,
                responsavel=ev_resp or None,
                motivo=ev_mot or None,
            )
            db.session.add(evento)
            _ev_created = True

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
                db.session.flush()
                compra.status = _calc_compra_status(compra)
                db.session.commit()
                flash("Compra atualizada!", "success")
                redirect_after = request.form.get("redirect_after")
                if redirect_after:
                    return redirect(redirect_after)
                return redirect(url_for("compras.edit", id=compra.id))
        else:
            db.session.flush()
            compra.status = _calc_compra_status(compra)
            db.session.commit()
            flash("Compra atualizada!", "success")
            redirect_after = request.form.get("redirect_after")
            if redirect_after:
                return redirect(redirect_after)
            return redirect(url_for("compras.edit", id=compra.id))

    contas = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([1, 2])).order_by(Conta.nome).all()
    insumos = Ingredient.query.order_by(Ingredient.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes] if transacao else []
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "sys_compras/form.html", transacao=transacao, compra=compra,
        contas=contas, insumos=insumos,
        carteiras=carteiras,
        PREVISAO_STATUS=PREVISAO_STATUS, COMPRA_STATUS=COMPRA_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Pagamento",
    )


@bp.route("/<int:id>/print")
def print_compra(id):
    compra = Compra.query.get_or_404(id)
    return render_template("sys_compras/print_compra.html", compra=compra,
                           COMPRA_STATUS=COMPRA_STATUS)


@bp.route("/<int:id>/pdf")
def pdf_compra(id):
    compra = Compra.query.get_or_404(id)
    from app.reports.compra import COMPRA_REPORT
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(COMPRA_REPORT, compra.items, logo_path, instance=compra)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=compra_{compra.id}.pdf"})
