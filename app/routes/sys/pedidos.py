from datetime import date, datetime, timezone, timedelta
from io import BytesIO
from app.utils import parse_brl, parse_prazo_recebimento, _save_event, _clean
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from flask_login import login_required
import os
from app.extensions import db
from app.models.client import Conta
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.event import Event
from app.models.quote import Quote
from app.pdf import gerar_pdf_relatorio
from app.models.carteira import Carteira
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.models.producao import Producao  # noqa: needed for Order mapper resolution
from app.models.operacao import Operacao  # noqa: needed for Transacao mapper resolution
from app.constantes import ORDER_STATUS, QUOTE_STATUS, FORMINHAS, PREVISAO_STATUS
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter, build_fk_options
from app.ajsystem.list import build_field_context, build_filter_config, List
from app.form import Form, handle_form

from app.fields import FIELD_ID, FIELD_DATA_HORA, FIELD_TOTAL, FIELD_STATUS, FIELD_OBS, FIELD_TIPO, FIELD_HORA, FIELD_QUANTIDADE, FIELD_PRECO, FIELD_DATA, FIELD_DOCUMENTO, FIELD_VENCIMENTO, FIELD_PREVISTO, FIELD_REALIZADO, FIELD_VARIACAO, FIELD_SALDO, FIELD_VALOR, FIELD_HISTORICO


tipos_evento_list = [
    "Aniversário", "Casamento", "Debutante", "Corporativo",
    "Infantil", "Família", "Confraternização", "Religioso", "Outros",
]
tipos_evento = {t: t for t in tipos_evento_list}


PEDIDOS_FIELDS = {'model': Order, 'fields': {
    'id':                    FIELD_ID,
    'cliente':               {'label': 'Cliente', 'width': 20, 'query': 'conta', 'card_path': 'conta.nome', 'in_form': False, 'filter_path': 'conta.nome'},
    'client_id':             {'label': 'Cliente', 'width': 8, 'input': 'select', 'query': 'conta',
                               'required': True, 'query_filter': {'ativo': True, 'tipo': [0, 1]}},
    'data_pedido':           {**FIELD_DATA_HORA, 'width': 10},
    'data_previsao_entrega': {**FIELD_DATA_HORA, 'width': 10, 'label': 'Prev. Entrega'},
    'data_entrega':          {**FIELD_DATA_HORA, 'width': 10},
    'carteira':              {'label': 'Pagamento', 'width': 15, 'query': 'carteira', 'in_form': False, 'filter_path': 'carteira.nome'},
    'carteira_id':           {'width': 12, 'input': 'select', 'query': 'carteira',
                               'query_filter': {'uso': [0, 1]},
                               'attrs': {'id': 'carteira-select'}},
    'forminhas':             {'width': 12, 'input': 'select', 'options': FORMINHAS},
    'total':                 {**FIELD_TOTAL, 'width': 10},
    'status':                {**FIELD_STATUS, 'width': 10, 'options': ORDER_STATUS},
    'transacao':             {'label': 'Faturado', 'width': 10, 'filter': False, 'in_form': False},
    'quote_id':              {'label': 'Orçamento', 'width': 9, 'filter': False, 'link': 'orcamentos.form', 'in_form': False},
}}

pedidos_list = {'fields': PEDIDOS_FIELDS, 'edit_endpoint': 'pedidos.form', 'send_endpoint': 'pedidos.print_order'}


def _replace_order_items(order, form):
    for item in list(order.items):
        db.session.delete(item)
    produtos = form.getlist("product_id")
    quantidades = form.getlist("quantidade")
    precos = form.getlist("preco_unitario")
    obs_itens = form.getlist("observacao_item")
    total = 0
    for pid, qtd, prc, obs in zip(produtos, quantidades, precos, obs_itens):
        if not pid or not qtd:
            continue
        product = Product.query.get(int(pid))
        qtd_val = int(qtd)
        _prc = parse_brl(prc)
        prc_val = product.preco if _prc is None else _prc
        item = OrderItem(
            order_id=order.id, product_id=product.id,
            quantidade=qtd_val, preco_unitario=prc_val,
            observacao=_clean(obs),
        )
        db.session.add(item)
        total += float(prc_val) * qtd_val
    return total


def _orders_pre_save(instance, request, is_new):
    data_entrega_str = request.form.get("data_entrega")
    if data_entrega_str:
        instance.data_entrega = datetime.strptime(data_entrega_str, "%Y-%m-%dT%H:%M")
        instance.status = 9
    else:
        instance.data_entrega = None
        instance.status = int(request.form.get("status", instance.status if not is_new else 0))
        if instance.status == 0:
            instance.status = 1
        if instance.status == 9:
            instance.status = 1

    data_previsao_str = request.form.get("data_previsao_entrega")
    if data_previsao_str:
        instance.data_previsao_entrega = datetime.strptime(data_previsao_str, "%Y-%m-%dT%H:%M")
    else:
        instance.data_previsao_entrega = None

    instance.carteira_id = request.form.get("carteira_id", type=int) or None
    instance.forminhas = request.form.get("forminhas", 0, type=int)
    instance.observacao = request.form.get("observacao", "")

    _save_event(instance, request.form)

    total = _replace_order_items(instance, request.form)
    instance.total = total

    if not instance.quote_id:
        quote = Quote.query.filter_by(pedido_id=instance.id).first()
        if quote:
            instance.quote_id = quote.id


ITENS_FIELDS = {'model': OrderItem, 'type': 'table', 'template': 'sys_orders/_itens.html', 'fields': {
    'product_id':      {'label': 'Produto', 'input': 'select'},
    'quantidade':      {**FIELD_QUANTIDADE, 'label': 'Qtd'},
    'preco_unitario':  {**FIELD_PRECO, 'label': 'Preço'},
    'observacao_item': {'label': 'Obs'},
}}

EVENT_FIELDS = {'model': Event, 'fields': {
    'tipo':       {**FIELD_TIPO, 'options': tipos_evento},
    'tema':       {},
    'convidados': {**FIELD_QUANTIDADE, 'label': 'Nº Convidados'},
    'obs':        {**FIELD_OBS},
    'data':       {**FIELD_DATA},
    'hora':       {**FIELD_HORA},
    'local':      {},
    'cerimonial': {},
}}

PREVISAO_FIELDS = {'model': Previsao, 'fields': {
    'transacao_id': {'label': 'Transação', 'link': 'transacao.receber_edit'},
    'id':           {'label': 'Previsão'},
    'documento':    FIELD_DOCUMENTO,
    'vencimento':   FIELD_VENCIMENTO,
    'previsto':     FIELD_PREVISTO,
    'realizado':    FIELD_REALIZADO,
    'variacao':     FIELD_VARIACAO,
    'saldo':        FIELD_SALDO,
}}

MOVTO_FIELDS = {'model': Movto, 'fields': {
    'id':        {'label': 'Recebimento', 'link': 'movimentos.recebimentos_form'},
    'recurso':   { 'query': 'recurso'},
    'valor':     FIELD_VALOR,
    'historico': FIELD_HISTORICO,
}}

gerar_btn = {'label': 'Gerar Financeiro', 'endpoint': 'pedidos.gerar_financeiro',
             'icon': 'bi-cash-coin', 'color': 'success', 'outline': False,
             'url_var': 'id', 'show_if': ('transacao_id', None)}

Form = {'model': Order, 'redirect': 'pedidos.list', 'fields': PEDIDOS_FIELDS, 'sessions': {
        'Itens do Pedido': ITENS_FIELDS,
        'Evento':           EVENT_FIELDS,
        '*Financeiro': {
            'buttons': [gerar_btn],
        },
        'A RECEBER': {
            'type': 'table', 'attr': 'transacao.previsoes',
            'fields': PREVISAO_FIELDS,
            'when': lambda i: i is not None and i.transacao is not None,
        },
        'RECEBIMENTO': {
            'type': 'table', 'attr': 'movto',
            'fields': MOVTO_FIELDS,
            'when': lambda i: i is not None and i.movto is not None,
        },
    }, 'readonly_when': {'status': [9]}, 'pre_save': _orders_pre_save, 'flash_ok': 'Pedido criado!', 'flash_update': 'Pedido atualizado!',
    'new_label': 'Pedido', 'new_title': 'Novo Pedido',
    'body_template': 'sys_orders/_form_body.html',
    'nav_right_extra': 'sys_orders/_nav_right.html',
    'footer_left': 'sys_orders/_footer_left.html',
    'page_scripts': 'sys_orders/_page_scripts.html',
}


bp = Blueprint("pedidos", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/dashboard")
def dashboard():
    hoje = date.today()
    orders = Order.query.order_by(Order.data_entrega).all()
    grupos = {}
    for o in orders:
        grupos.setdefault(o.status, []).append(o)
    ordem_status = [0, 1, 2, 9]
    grupos_ordenados = {s: grupos.get(s, []) for s in ordem_status}
    return render_template("index.html")


@bp.route("/pedidos", endpoint="list")
def order_list():
    _list = List(**pedidos_list)
    filter_config = build_filter_config(PEDIDOS_FIELDS)
    active = resolve_filters(filter_config, request.args)
    q = Order.query.options(
        db.joinedload(Order.conta), db.joinedload(Order.carteira),
    ).order_by(Order.data_entrega)
    orders = q.all()
    linhas = orders[:]
    linhas = apply_select_filter(linhas, 'status', active.get('status'), ORDER_STATUS)
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_select_filter(linhas, 'cliente', active.get('cliente'), build_fk_options(Conta), filter_path='conta.nome')
    linhas = apply_date_filter(linhas, 'data_pedido', active.get('data_pedido'))
    linhas = apply_date_filter(linhas, 'data_previsao_entrega', active.get('data_previsao_entrega'))
    linhas = apply_date_filter(linhas, 'data_entrega', active.get('data_entrega'))
    linhas = apply_select_filter(linhas, 'forminhas', active.get('forminhas'), FORMINHAS)
    linhas = apply_select_filter(linhas, 'carteira', active.get('carteira'), build_fk_options(Carteira), filter_path='carteira.nome')
    linhas = apply_number_filter(linhas, 'total', active.get('total'))
    orders = linhas
    ctx = build_field_context(PEDIDOS_FIELDS)
    return render_template("index.html")


@bp.route("/pedidos/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/pedidos/<int:id>/editar", methods=["GET", "POST"])
def form(id=None):
    if id is not None:
        order = Order.query.get(id)
        if not order:
            flash("Código inexistente", "warning")
            return redirect(url_for("pedidos.list"))
        if not order.quote_id:
            q = Quote.query.filter_by(pedido_id=order.id).first()
            if q:
                order.quote_id = q.id
                db.session.commit()
    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    carteiras = Carteira.query.filter(Carteira.uso.in_([0, 1])).order_by(Carteira.nome).all()
    return handle_form(Form, id, extra_ctx={
        'products': products,
        'carteiras': carteiras,
        'tipos_evento': tipos_evento_list,
        'ORDER_STATUS': ORDER_STATUS,
        'FORMINHAS': FORMINHAS,
        'PREVISAO_STATUS': PREVISAO_STATUS,
    })


@bp.route("/pedidos/<int:id>/status", methods=["POST"])
def status(id):
    order = Order.query.get_or_404(id)
    if order.status == 9:
        flash("Pedido entregue não pode ter status alterado.", "warning")
        return redirect(url_for("pedidos.form", id=id))
    novo_status = request.form["status"]
    if novo_status == "9" and not order.data_entrega:
        flash("Status Entregue só pode ser definido preenchendo a data de entrega.", "warning")
        return redirect(url_for("pedidos.form", id=id))
    if novo_status in ("0", "1", "2", "8", "9"):
        order.status = int(novo_status)
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("pedidos.form", id=id))


@bp.route("/pedidos/<int:id>/cancelar", methods=["POST"])
def cancel(id):
    order = Order.query.get_or_404(id)
    if order.status == 9:
        flash("Pedido entregue não pode ser cancelado.", "warning")
        return redirect(url_for("pedidos.form", id=id))
    order.status = 3
    if order.transacao:
        order.transacao.cancelado = date.today()
    db.session.commit()
    flash("Pedido cancelado!", "success")
    return redirect(url_for("pedidos.form", id=id))


@bp.route("/pedidos/<int:id>/print")
def print_order(id):
    order = Order.query.get_or_404(id)
    from app.reports.rep_pedido import PEDIDO_REPORT
    return render_template(
        PEDIDO_REPORT.print_template,
        fallback_url=url_for(PEDIDO_REPORT.edit_endpoint, id=order.id),
        pdf_url=url_for('pedidos.pdf_order', id=order.id),
    )


@bp.route("/pedidos/<int:id>/pdf")
def pdf_order(id):
    order = Order.query.get_or_404(id)
    from app.reports.rep_pedido import PEDIDO_REPORT
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(PEDIDO_REPORT, order.items, logo_path, instance=order)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=pedido_{order.id}.pdf"})


@bp.route("/pedidos/<int:id>/gerar-financeiro", methods=["GET", "POST"])
def gerar_financeiro(id):
    order = Order.query.get_or_404(id)
    if order.transacao_id or order.movto_id:
        flash("Financeiro já gerado para este pedido.", "warning")
        return redirect(url_for("pedidos.form", id=id))

    fp = order.carteira
    if not fp:
        flash("Selecione uma forma de pagamento antes de gerar o financeiro.", "warning")
        return redirect(url_for("pedidos.form", id=id))

    total = float(order.total or 0)
    taxa = float(fp.taxa_recebimento or 0)
    valor_liquido = round(total * (1 - taxa / 100), 2)

    if request.method == "POST":
        if fp.gerar == 0:
            recurso_id = request.form.get("recurso_id", type=int)
            if not recurso_id:
                flash("Selecione um recurso.", "warning")
                return redirect(url_for("pedidos.gerar_financeiro", id=id))
            movto = Movto(
                data=request.form.get("data", order.data_pedido.date()),
                recurso_id=recurso_id,
                tipo="E",
                conta_id=order.client_id,
                valor=valor_liquido,
                historico=request.form.get("historico", f"Recebimento Pedido #{order.id}"),
                carteira_id=fp.id,
            )
            db.session.add(movto)
            db.session.flush()
            order.movto_id = movto.id
        else:
            transacao = Transacao(
                data=order.data_pedido.date(),
                tipo="V",
                conta_id=order.client_id,
                valor=total,
                historico=order.observacao or f"Venda Pedido #{order.id}",
            )
            db.session.add(transacao)
            db.session.flush()
            order.transacao_id = transacao.id

            parcelas = parse_prazo_recebimento(
                fp.prazo_recebimento,
                order.data_pedido.date(),
                order.data_entrega.date() if order.data_entrega else None,
                total,
            )
            for p in parcelas:
                previsao = Previsao(
                    transacao_id=transacao.id,
                    vencimento=p["vencimento"],
                    previsto=p["previsto"],
                    carteira_id=fp.id,
                    taxa=taxa,
                )
                db.session.add(previsao)

            prev_total = sum(float(p["previsto"]) for p in parcelas)
            transacao.total_previsto = prev_total

        db.session.commit()
        flash("Financeiro gerado com sucesso!", "success")
        return redirect(url_for("pedidos.form", id=id))

    recursos = Recurso.query.order_by(Recurso.nome).all()
    parcelas = []
    if fp.gerar == 1:
        parcelas = parse_prazo_recebimento(
            fp.prazo_recebimento,
            order.data_pedido.date(),
            order.data_entrega.date() if order.data_entrega else None,
            total,
        )

    return render_template("index.html")
