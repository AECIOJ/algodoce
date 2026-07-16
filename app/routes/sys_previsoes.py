from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.previsao import Previsao
from app.models.client import Conta
from app.models.operacao import Operacao
from app.constants import TIPO_PREVISAO, TIPO_OPERACAO, PREVISAO_STATUS
from app.table import Field, build_field_context, Table
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter, build_fk_options, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT


PREVISOES_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='data', label='Data', width=10, input='date'),
    Field(name='tipo', label='Tipo', width=8, options=TIPO_PREVISAO, filter_options=TIPO_PREVISAO),
    Field(name='status', label='Status', width=10, options=PREVISAO_STATUS, filter_options=PREVISAO_STATUS),
    Field(name='conta', label='Conta', width=15, query='conta'),
    Field(name='documento', label='Documento', width=10),
    Field(name='vencimento', label='Vencimento', width=10, input='date'),
    Field(name='previsto', label='Previsto', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='variacao', label='Variação', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='realizado', label='Realizado', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='saldo', label='Saldo', width=10, input='number', align='right', aggregate='sum', currency='brl'),
]

PREVISOES_TABLE = Table(fields=PREVISOES_FIELDS, edit_endpoint='previsoes.edit')

PREVISOES_FILTERS = {
    'id':         MODE_NUMBER,
    'data':       MODE_DATE,
    'tipo':       {**MODE_SELECT, 'options': TIPO_PREVISAO},
    'status':     {**MODE_SELECT, 'options': PREVISAO_STATUS},
    'conta':      {**MODE_SELECT, 'filter_path': 'transacao.conta.nome'},
    'documento':  MODE_TEXT,
    'vencimento': MODE_DATE,
    'previsto':   MODE_NUMBER,
    'variacao':   MODE_NUMBER,
    'realizado':  MODE_NUMBER,
    'saldo':      MODE_NUMBER,
}

bp = Blueprint("previsoes", __name__, url_prefix="/previsoes")


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/")
def list():
    hoje = date.today()
    active = resolve_filters(PREVISOES_FILTERS, request.args)
    tipo_cfg = active.get('tipo')
    query = Previsao.query.order_by(Previsao.vencimento, Previsao.id)
    if tipo_cfg:
        tipo_key = next((k for k, v in TIPO_PREVISAO.items() if v == tipo_cfg), None)
        if tipo_key is not None:
            query = query.filter_by(tipo=tipo_key)
    previsoes = query.all()
    linhas = previsoes[:]
    linhas = apply_select_filter(linhas, 'status', active.get('status'), PREVISAO_STATUS)
    linhas = apply_date_filter(linhas, 'vencimento', active.get('vencimento'))
    linhas = apply_date_filter(linhas, 'data', active.get('data'))
    linhas = apply_select_filter(linhas, 'conta', active.get('conta'), build_fk_options(Conta), filter_path='transacao.conta.nome')
    linhas = apply_text_filter(linhas, 'documento', active.get('documento'))
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_number_filter(linhas, 'previsto', active.get('previsto'))
    linhas = apply_number_filter(linhas, 'realizado', active.get('realizado'))
    linhas = apply_number_filter(linhas, 'variacao', active.get('variacao'))
    linhas = apply_number_filter(linhas, 'saldo', active.get('saldo'))
    previsoes = linhas
    total_saldo = sum(
        float(p.previsto + (p.variacao or 0) - (p.realizado or 0))
        for p in previsoes
    )
    ctx = build_field_context(PREVISOES_FIELDS, filters_config=PREVISOES_FILTERS)
    return render_template(
        "sys_previsoes/list.html", previsoes=previsoes, total_saldo=total_saldo,
        PREVISOES_TABLE=PREVISOES_TABLE, ctx=ctx,
        TIPO_PREVISAO=TIPO_PREVISAO, PREVISAO_STATUS=PREVISAO_STATUS,
        active_filters=active, FILTERS=PREVISOES_FILTERS,
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
