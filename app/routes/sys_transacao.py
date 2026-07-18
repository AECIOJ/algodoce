from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.previsao import Previsao
from app.models.transacao import Transacao
from app.models.client import Conta
from app.models.operacao import Operacao
from app.models.movto import Movto
from app.models.compra import Compra
from app.models.order import Order
from app.models.compra_historico import CompraHistorico
from app.constants import PREVISAO_STATUS
from app.utils import LinhaTransacao, parse_prazo_recebimento
from app.table import Field, build_field_context, Table
from app.filters import resolve_filters, apply_select_filter, apply_date_filter, apply_text_filter, apply_number_filter, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT


TRANSACAO_FIELDS = [
    Field(name='transacao_id', label='Transação', width=8, card_path='transacao.id'),
    Field(name='conta', label='Conta', width=15, query='conta'),
    Field(name='compra_id', label='Compra', width=6, link='compras.edit'),
    Field(name='fatura', label='Fatura', width=10),
    Field(name='valor', label='Valor', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='id', label='Previsão', width=8),
    Field(name='documento', label='Documento', width=10),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='status', label='Status', width=10, options=PREVISAO_STATUS, filter_options=PREVISAO_STATUS),
]

TIPO_PAGAR = ("P", "C")
TIPO_RECEBER = ("R", "V")
TIPO_NOME = {"P": "Pagamento", "R": "Recebimento"}
TIPO_NOME_PLURAL = {"P": "Pagamentos", "R": "Recebimentos"}

TRANSACAO_FILTERS = {
    'transacao_id': MODE_NUMBER,
    'conta':        {**MODE_SELECT},
    'compra_id':    MODE_NUMBER,
    'fatura':       MODE_TEXT,
    'valor':        MODE_NUMBER,
    'id':           MODE_NUMBER,
    'documento':    MODE_TEXT,
    'vencimento':   MODE_DATE,
    'previsto':     MODE_NUMBER,
    'realizado':    MODE_NUMBER,
    'variacao':     MODE_NUMBER,
    'saldo':        MODE_NUMBER,
    'status':       {**MODE_SELECT, 'options': PREVISAO_STATUS},
}

bp = Blueprint("transacao", __name__, url_prefix="/transacao")


def _build_submitted():
    data = {
        "data": request.form.get("data"),
        "conta_id": request.form.get("conta_id"),
        "operacao_id": request.form.get("operacao_id"),
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


def _nav_ids(query_tipo):
    query = Transacao.query.with_entities(Transacao.id).filter(Transacao.tipo.in_(query_tipo)).order_by(Transacao.id)
    return [t.id for t in query.all()]


def _build_nav(ids, current_id):
    try:
        idx = ids.index(current_id)
        return {
            "first_id": ids[0],
            "last_id": ids[-1],
            "prev_id": ids[idx - 1] if idx > 0 else None,
            "next_id": ids[idx + 1] if idx < len(ids) - 1 else None,
        }
    except ValueError:
        return {"first_id": None, "last_id": None, "prev_id": None, "next_id": None}


def _salvar_previsoes(transacao, submitted_data, submitted_previsoes):
    ids = request.form.getlist("previsao_id[]")
    docs = request.form.getlist("previsao_documento[]")
    vencs = request.form.getlist("previsao_vencimento[]")
    prevs = request.form.getlist("previsao_previsto[]")
    reals = request.form.getlist("previsao_realizado[]")
    vars_ = request.form.getlist("previsao_variacao[]")
    removes = request.form.getlist("previsao_remover[]")

    existing = {p.id for p in transacao.previsoes}
    submitted = set()
    deleted = set()

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


@bp.before_request
@login_required
def protect():
    pass


# ── HELPERS COMPARTILHADOS ───────────────────────────────────────────

def _list(tipo):
    is_pagar = tipo in ("P", "C")
    tipos = TIPO_PAGAR if is_pagar else TIPO_RECEBER
    hoje = date.today()
    active = resolve_filters(TRANSACAO_FILTERS, request.args)
    transacoes = Transacao.query.options(
        joinedload(Transacao.previsoes)
    ).filter(
        Transacao.tipo.in_(tipos)
    ).order_by(Transacao.data, Transacao.id).all()

    linhas = []
    for t in transacoes:
        if t.previsoes:
            for p in t.previsoes:
                linhas.append(LinhaTransacao(t, p))
        else:
            linhas.append(LinhaTransacao(t))

    linhas = apply_select_filter(linhas, 'status', active.get('status'), PREVISAO_STATUS)
    linhas = apply_date_filter(linhas, 'vencimento', active.get('vencimento'))
    linhas = apply_select_filter(linhas, 'conta', active.get('conta'), {c.nome for c in Conta.query.all()})
    linhas = apply_text_filter(linhas, 'fatura', active.get('fatura'))
    linhas = apply_number_filter(linhas, 'transacao_id', active.get('transacao_id'))
    linhas = apply_number_filter(linhas, 'compra_id', active.get('compra_id'))
    linhas = apply_text_filter(linhas, 'documento', active.get('documento'))
    linhas = apply_number_filter(linhas, 'valor', active.get('valor'))
    linhas = apply_number_filter(linhas, 'previsto', active.get('previsto'))
    linhas = apply_number_filter(linhas, 'realizado', active.get('realizado'))
    linhas = apply_number_filter(linhas, 'variacao', active.get('variacao'))
    linhas = apply_number_filter(linhas, 'saldo', active.get('saldo'))

    total_saldo = sum(l.saldo for l in linhas)
    ctx = build_field_context(TRANSACAO_FIELDS, filters_config=TRANSACAO_FILTERS)
    table = Table(
        fields=TRANSACAO_FIELDS,
        fields_master=[1, 2, 3, 4, 5],
        fields_detail=[6, 7, 8, 9, 10, 11, 12, 13],
        master_key='transacao_id',
        edit_endpoint='transacao.pagar_edit' if is_pagar else 'transacao.receber_edit',
        edit_id_field='transacao.id')
    return render_template(
        "sys_transacao/list.html", previsoes=linhas, total_saldo=total_saldo,
        TABLE=table, ctx=ctx, tipo=tipo,
        tipo_nome=TIPO_NOME[tipo], tipo_nome_plural=TIPO_NOME_PLURAL[tipo],
        PREVISAO_STATUS=PREVISAO_STATUS, active_filters=active, FILTERS=TRANSACAO_FILTERS)


def _detail(id, tipo):
    is_pagar = tipo in ("P", "C")
    transacao = Transacao.query.options(joinedload(Transacao.previsoes)).get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("transacao.pagar_list" if is_pagar else "transacao.receber_list"))
    return render_template(
        "sys_transacao/detalhes.html", t=transacao,
        hoje=date.today(), PREVISAO_STATUS=PREVISAO_STATUS,
        tipo=tipo,
        back_url=url_for("transacao.pagar_list" if is_pagar else "transacao.receber_list"),
        edit_url=url_for("transacao.pagar_edit" if is_pagar else "transacao.receber_edit", id=id))


def _excluir(id, tipo):
    is_pagar = tipo in ("P", "C")
    list_endpoint = "transacao.pagar_list" if is_pagar else "transacao.receber_list"
    transacao = Transacao.query.get(id)
    if not transacao:
        flash("Registro inexistente", "warning")
        return redirect(url_for(list_endpoint))
    if transacao.previsoes:
        flash("Exclua as parcelas antes de excluir a transação", "danger")
        return redirect(url_for(list_endpoint))
    compra = Compra.query.filter_by(transacao_id=transacao.id).first()
    order = Order.query.filter_by(transacao_id=transacao.id).first()
    if compra:
        compra.transacao_id = None
    if order:
        order.transacao_id = None
    db.session.delete(transacao)
    db.session.commit()
    flash("Conta excluída!", "success")
    if is_pagar and compra:
        return redirect(url_for("compras.edit", id=compra.id))
    if not is_pagar and order:
        return redirect(url_for("orders.edit", id=order.id))
    return redirect(url_for(list_endpoint))


# ── ENDPOINTS PÚBLICOS (list / detail / excluir) ─────────────────────

@bp.route("/pagar/")
def pagar_list():
    return _list("P")

@bp.route("/receber/")
def receber_list():
    return _list("R")

@bp.route("/pagar/<int:id>/detalhes")
def pagar_detail(id):
    return _detail(id, "P")

@bp.route("/receber/<int:id>/detalhes")
def receber_detail(id):
    return _detail(id, "R")

@bp.route("/pagar/<int:id>/excluir", methods=["POST"])
def pagar_excluir(id):
    return _excluir(id, "P")

@bp.route("/receber/<int:id>/excluir", methods=["POST"])
def receber_excluir(id):
    return _excluir(id, "R")


# ── PAGAR (new / edit — lógica específica) ───────────────────────────

@bp.route("/pagar/novo", methods=["GET", "POST"])
def pagar_new():
    compra_id = request.args.get("compra_id", type=int) or request.form.get("compra_id", type=int)
    compra = Compra.query.get(compra_id) if compra_id else None
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "GET":
        if compra and compra.transacao_id:
            return redirect(url_for("transacao.pagar_edit", id=compra.transacao_id))
        contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
        operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
        submitted_data = None
        if compra:
            submitted_data = {
                "data": str(compra.data or date.today()),
                "conta_id": str(compra.fornecedor_id),
                "operacao_id": "",
                "fatura": f"C#{compra.id}",
                "valor": str(compra.valor or 0),
                "historico": compra.historico or "",
            }
        return render_template(
            "sys_transacao/pagar/form.html",
            contas=contas, operacoes=operacoes, hoje=date.today(),
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
            operacao_id=request.form.get("operacao_id", type=int) or None,
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
            operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
            return render_template(
                "sys_transacao/pagar/form.html",
                contas=contas, operacoes=operacoes, hoje=date.today(),
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                prazo_inicial=prazo_inicial,
                locked=False, transacao=None, nav={}, movimentos=[],
                PREVISAO_STATUS=PREVISAO_STATUS, tipo_nome="Pagamento",
            )

        if compra and abs(float(transacao.valor) - float(compra.valor or 0)) > 0.005:
            db.session.rollback()
            flash(f"Valor da transação ({transacao.valor:.2f}) difere do valor da compra ({float(compra.valor or 0):.2f})", "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
            return render_template(
                "sys_transacao/pagar/form.html",
                contas=contas, operacoes=operacoes, hoje=date.today(),
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                prazo_inicial=prazo_inicial,
                locked=False, transacao=None, nav={}, movimentos=[],
                PREVISAO_STATUS=PREVISAO_STATUS, tipo_nome="Pagamento",
            )

        if compra and not compra.transacao_id:
            compra.transacao_id = transacao.id
            evento = CompraHistorico(
                compra_id=compra.id, status=2, data=transacao.data,
                usuario=current_user.username if current_user.is_authenticated else None,
                responsavel=current_user.username if current_user.is_authenticated else None,
            )
            db.session.add(evento)
            compra.status = compra.calc_status()
            db.session.commit()
        else:
            db.session.commit()
        flash("Conta cadastrada!", "success")
        return redirect(url_for("transacao.pagar_list"))


@bp.route("/pagar/<int:id>/editar", methods=["GET", "POST"])
def pagar_edit(id):
    transacao = Transacao.query.get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("transacao.pagar_list"))

    nav = _build_nav(_nav_ids(TIPO_PAGAR), id)

    locked = bool(Compra.query.filter_by(transacao_id=transacao.id).first())
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "POST":
        submitted_data, submitted_previsoes = _build_submitted()

        if not locked:
            cancelado = request.form.get("cancelado") or None
            transacao.data = request.form.get("data") or date.today()
            transacao.conta_id = request.form.get("conta_id", type=int) or None
            transacao.operacao_id = request.form.get("operacao_id", type=int) or None
            transacao.fatura = request.form.get("fatura") or None
            transacao.valor = float(request.form.get("valor", 0))
            transacao.cancelado = cancelado
            transacao.historico = request.form.get("historico") or None

        _salvar_previsoes(transacao, submitted_data, submitted_previsoes)

        compra = transacao.compra
        errors = []
        if compra and abs(float(transacao.valor) - float(compra.valor or 0)) > 0.005:
            errors.append(f"Valor da transação ({transacao.valor:.2f}) difere do valor da compra ({float(compra.valor or 0):.2f})")

        if errors:
            db.session.rollback()
            for err in errors:
                flash(err, "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
            previsao_ids = [p.id for p in transacao.previsoes]
            movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
            return render_template(
                "sys_transacao/pagar/form.html", transacao=transacao,
                contas=contas, operacoes=operacoes,
                PREVISAO_STATUS=PREVISAO_STATUS,
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes, nav=nav,
                movimentos=movimentos, tipo_nome="Pagamento", locked=locked,
                prazo_inicial=prazo_inicial,
            )
        else:
            db.session.commit()
            flash("Conta atualizada!", "success")
            return redirect(url_for("transacao.pagar_list"))

    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes]
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "sys_transacao/pagar/form.html", transacao=transacao,
        contas=contas, operacoes=operacoes,
        PREVISAO_STATUS=PREVISAO_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Pagamento", locked=locked,
        prazo_inicial=prazo_inicial,
    )


# ── RECEBER (new / edit — lógica específica) ─────────────────────────

@bp.route("/receber/novo", methods=["GET", "POST"])
def receber_new():
    order_id = request.args.get("order_id", type=int) or request.form.get("order_id", type=int)
    order = Order.query.get(order_id) if order_id else None
    back_url = url_for("orders.edit", id=order.id) if order else url_for("transacao.receber_list")
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "POST":
        submitted_data, submitted_previsoes = _build_submitted()

        cancelado = request.form.get("cancelado") or None
        transacao = Transacao(
            data=request.form.get("data") or date.today(),
            tipo='R',
            conta_id=request.form.get("conta_id", type=int) or None,
            operacao_id=request.form.get("operacao_id", type=int) or None,
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

        errors = []
        if order and abs(float(transacao.valor) - float(order.total or 0)) > 0.005:
            errors.append(f"Valor da transação ({transacao.valor:.2f}) difere do valor do pedido ({float(order.total or 0):.2f})")

        if errors:
            db.session.rollback()
            for err in errors:
                flash(err, "danger")
            contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
            operacoes = Operacao.query.filter_by(ativa=True, tipo=1).order_by(Operacao.ordem, Operacao.nome).all()
            return render_template(
                "sys_transacao/receber/form.html",
                contas=contas, operacoes=operacoes, hoje=date.today(),
                submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                back_url=back_url, prazo_inicial=prazo_inicial,
            )

        db.session.commit()

        if order and not order.transacao_id:
            order.transacao_id = transacao.id
            db.session.commit()

        flash("Conta cadastrada!", "success")
        return redirect(url_for("transacao.receber_list"))

    submitted_data = None
    submitted_previsoes = None
    if order:
        fp = order.carteira
        if fp and fp.gerar != 0:
            total = float(order.total or 0)
            data_entrega = order.data_entrega or order.data_previsao_entrega
            prazo = prazo_inicial or fp.prazo_recebimento
            parcelas = parse_prazo_recebimento(
                prazo,
                order.data_pedido.date(),
                data_entrega.date() if data_entrega else None,
                total,
            )
            submitted_data = {
                "data": str(order.data_pedido.date()),
                "conta_id": str(order.client_id),
                "operacao_id": "",
                "fatura": f"P#{order.id}",
                "valor": str(total),
                "historico": order.observacao or "",
            }
            submitted_previsoes = []
            for i, p in enumerate(parcelas):
                n_parcela = "U" if len(parcelas) == 1 else str(i + 1)
                submitted_previsoes.append({
                    "id": None,
                    "vencimento": str(p["vencimento"]),
                    "previsto": p["previsto"],
                    "realizado": None,
                    "variacao": 0,
                    "documento": f"{submitted_data['fatura']}/{n_parcela}",
                })

    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
    return render_template(
        "sys_transacao/receber/form.html",
        contas=contas, operacoes=operacoes, hoje=date.today(),
        submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
        back_url=back_url, prazo_inicial=prazo_inicial,
    )


@bp.route("/receber/<int:id>/editar", methods=["GET", "POST"])
def receber_edit(id):
    transacao = Transacao.query.get(id)
    if not transacao:
        flash("Código inexistente", "warning")
        return redirect(url_for("transacao.receber_list"))

    nav = _build_nav(_nav_ids(TIPO_RECEBER), id)

    locked = bool(Order.query.filter_by(transacao_id=transacao.id).first())
    prazo_inicial = request.args.get("prazo", "")

    if request.method == "POST":
        submitted_data, submitted_previsoes = _build_submitted()

        transacao.operacao_id = request.form.get("operacao_id", type=int) or None

        if not locked:
            cancelado = request.form.get("cancelado") or None
            transacao.data = request.form.get("data") or date.today()
            transacao.conta_id = request.form.get("conta_id", type=int) or None
            transacao.fatura = request.form.get("fatura") or None
            transacao.valor = float(request.form.get("valor", 0))
            transacao.cancelado = cancelado
            transacao.historico = request.form.get("historico") or None

        if not locked:
            _salvar_previsoes(transacao, submitted_data, submitted_previsoes)

            errors = []
            pedido = transacao.pedido
            if pedido and abs(float(transacao.valor) - float(pedido.total or 0)) > 0.005:
                errors.append(f"Valor da transação ({transacao.valor:.2f}) difere do valor do pedido ({float(pedido.total or 0):.2f})")

            if errors:
                db.session.rollback()
                for err in errors:
                    flash(err, "danger")
                contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
                operacoes = Operacao.query.filter_by(ativa=True, tipo=1).order_by(Operacao.ordem, Operacao.nome).all()
                previsao_ids = [p.id for p in transacao.previsoes]
                movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
                return render_template(
                    "sys_transacao/receber/form.html", transacao=transacao,
                    contas=contas, operacoes=operacoes,
                    PREVISAO_STATUS=PREVISAO_STATUS,
                    submitted_data=submitted_data, submitted_previsoes=submitted_previsoes,
                    nav=nav, movimentos=movimentos, tipo_nome="Recebimento", locked=locked,
                    prazo_inicial=prazo_inicial,
                )

        db.session.commit()
        flash("Conta atualizada!", "success")
        return redirect(url_for("transacao.receber_list"))

    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
    previsao_ids = [p.id for p in transacao.previsoes]
    movimentos = Movto.query.filter(Movto.previsao_id.in_(previsao_ids)).order_by(Movto.data, Movto.id).all() if previsao_ids else []
    return render_template(
        "sys_transacao/receber/form.html", transacao=transacao,
        contas=contas, operacoes=operacoes,
        PREVISAO_STATUS=PREVISAO_STATUS,
        submitted_data=None, submitted_previsoes=None, nav=nav,
        movimentos=movimentos, tipo_nome="Recebimento", locked=locked,
        prazo_inicial=prazo_inicial,
    )
