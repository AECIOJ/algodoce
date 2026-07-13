from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.previsao import Previsao
from app.models.client import Conta
from app.models.operacao import Operacao
from app.constants import TIPO_PREVISAO, TIPO_OPERACAO, PREVISAO_STATUS
from app.table import Field, build_field_context, Table


PREVISOES_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='data', label='Data', width=10, input='date'),
    Field(name='tipo', label='Tipo', width=8, options=TIPO_PREVISAO, filter_options=list(TIPO_PREVISAO.values())),
    Field(name='status', label='Status', width=10, options=PREVISAO_STATUS, filter_options=list(PREVISAO_STATUS.values())),
    Field(name='conta', label='Conta', width=15, query='conta'),
    Field(name='documento', label='Documento', width=10),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
]

PREVISOES_TABLE = Table(fields=PREVISOES_FIELDS, edit_endpoint='previsoes.edit')

bp = Blueprint("previsoes", __name__, url_prefix="/previsoes")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    hoje = date.today()
    tipo = request.args.get("tipo", "todos")
    filtro_status = request.args.get("status", "todos")
    filtro_venc = request.args.get("vencimento", "todos")
    query = Previsao.query.order_by(Previsao.vencimento, Previsao.id)
    if tipo in ("P", "R"):
        query = query.filter_by(tipo=tipo)
    if filtro_venc == "em_atraso":
        query = query.filter(Previsao.vencimento < hoje)
    elif filtro_venc == "hoje":
        w = hoje.weekday()
        if w == 5:
            dias = [hoje, hoje + timedelta(days=1), hoje + timedelta(days=2)]
            query = query.filter(Previsao.vencimento.in_(dias))
        elif w == 6:
            dias = [hoje, hoje - timedelta(days=1), hoje + timedelta(days=1)]
            query = query.filter(Previsao.vencimento.in_(dias))
        elif w == 0:
            dias = [hoje, hoje - timedelta(days=1), hoje - timedelta(days=2)]
            query = query.filter(Previsao.vencimento.in_(dias))
        else:
            query = query.filter(Previsao.vencimento == hoje)
    elif filtro_venc == "a_vencer":
        query = query.filter(Previsao.vencimento > hoje)
    previsoes = query.all()
    if filtro_status != "todos":
        previsoes = [p for p in previsoes if p.status == int(filtro_status)]
    if filtro_venc in ("em_atraso", "hoje", "a_vencer"):
        previsoes = [p for p in previsoes if p.status < 8]
    total_saldo = sum(
        float(p.previsto + (p.variacao or 0) - (p.realizado or 0))
        for p in previsoes
    )
    ctx = build_field_context(PREVISOES_FIELDS)
    return render_template(
        "sys_previsoes/list.html", previsoes=previsoes, total_saldo=total_saldo,
        PREVISOES_TABLE=PREVISOES_TABLE, ctx=ctx,
        TIPO_PREVISAO=TIPO_PREVISAO, PREVISAO_STATUS=PREVISAO_STATUS,
    )


@bp.route("/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        cancelado = request.form.get("cancelado") or None
        previsto = float(request.form["previsto"])
        _realizado = request.form.get("realizado")
        realizado = float(_realizado) if _realizado else None
        _variacao = request.form.get("variacao")
        variacao = float(_variacao) if _variacao else 0
        previsao = Previsao(
            data=request.form.get("data") or date.today(),
            tipo=request.form["tipo"],
            conta_id=request.form.get("conta_id", type=int) or None,
            documento=request.form.get("documento") or None,
            vencimento=request.form["vencimento"],
            previsto=previsto,
            realizado=realizado,
            variacao=variacao,
            operacao_id=request.form.get("operacao_id", type=int) or None,
            cancelado=cancelado,
            historico=request.form.get("historico") or None,
        )
        db.session.add(previsao)
        db.session.commit()
        flash("Previsão cadastrada!", "success")
        return redirect(url_for("previsoes.list"))
    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
    return render_template(
        "sys_previsoes/form.html", TIPO_PREVISAO=TIPO_PREVISAO,
        PREVISAO_STATUS=PREVISAO_STATUS,
        contas=contas, operacoes=operacoes,
    )


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    previsao = Previsao.query.get(id)
    if not previsao:
        flash("Código inexistente", "warning")
        return redirect(url_for("previsoes.list"))
    if request.method == "POST":
        previsao.data = request.form.get("data") or date.today()
        previsao.tipo = request.form["tipo"]
        previsao.conta_id = request.form.get("conta_id", type=int) or None
        previsao.documento = request.form.get("documento") or None
        previsao.vencimento = request.form["vencimento"]
        previsao.previsto = float(request.form["previsto"])
        _realizado = request.form.get("realizado")
        previsao.realizado = float(_realizado) if _realizado else None
        _variacao = request.form.get("variacao")
        previsao.variacao = float(_variacao) if _variacao else 0
        previsao.operacao_id = request.form.get("operacao_id", type=int) or None
        cancelado = request.form.get("cancelado") or None
        previsao.cancelado = cancelado
        previsao.historico = request.form.get("historico") or None
        db.session.commit()
        flash("Previsão atualizada!", "success")
        return redirect(url_for("previsoes.list"))

    contas = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    operacoes = Operacao.query.filter_by(ativa=True).order_by(Operacao.ordem, Operacao.nome).all()
    return render_template(
        "sys_previsoes/form.html", previsao=previsao,
        TIPO_PREVISAO=TIPO_PREVISAO, PREVISAO_STATUS=PREVISAO_STATUS,
        contas=contas, operacoes=operacoes,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
def delete(id):
    previsao = Previsao.query.get_or_404(id)
    if previsao.movtos:
        flash("Exclua os movimentos antes de excluir a previsão", "danger")
        return redirect(url_for("previsoes.list"))
    t = previsao.transacao
    db.session.delete(previsao)
    if t:
        prev_total = sum(float(p.previsto) for p in t.previsoes if p.id != previsao.id)
        t.total_previsto = prev_total
    db.session.commit()
    flash("Previsão excluída!", "success")
    return redirect(url_for("previsoes.list"))
