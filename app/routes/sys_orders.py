from datetime import date, datetime, timezone, timedelta
from io import BytesIO
from app.utils import parse_brl, parse_prazo_recebimento, _save_event, _clean
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from flask_login import login_required
import os
from sqlalchemy import func
from app.extensions import db
from app.models.client import Conta
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.pdf import gerar_pdf_pedido, gerar_pdf_relatorio
from app.models.carteira import Carteira
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.constants import ORDER_STATUS, QUOTE_STATUS, FORMINHAS, PREVISAO_STATUS
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter, build_fk_options, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT
from app.table import Field, build_field_context, Table


ORDERS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='cliente', label='Cliente', width=20, query='conta', card_path='conta.nome'),
    Field(name='data_pedido', label='Data Pedido', width=10, input='date'),
    Field(name='data_previsao_entrega', label='Previsão Entrega', width=10, input='date'),
    Field(name='data_entrega', label='Data Entrega', width=10, input='date'),
    Field(name='forminhas', label='Forminhas', width=12, options=FORMINHAS, filter_options=FORMINHAS),
    Field(name='carteira', label='Pagamento', width=15, query='carteira'),
    Field(name='total', label='Total', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='status', label='Status', width=10, options=ORDER_STATUS, filter_options=ORDER_STATUS),
    Field(name='transacao', label='Faturado', width=10, filter=False),
    Field(name='quote_id', label='Orçamento', width=9, filter=False, link='orcamentos.form'),
]

ORDERS_TABLE = Table(fields=ORDERS_FIELDS, edit_endpoint='orders.edit', send_endpoint='orders.print_order')

ORDERS_FILTERS = {
    'id':                    MODE_NUMBER,
    'cliente':               {**MODE_SELECT, 'filter_path': 'conta.nome'},
    'data_pedido':           MODE_DATE,
    'data_previsao_entrega': MODE_DATE,
    'data_entrega':          MODE_DATE,
    'forminhas':             {**MODE_SELECT, 'options': FORMINHAS},
    'carteira':              {**MODE_SELECT, 'filter_path': 'carteira.nome'},
    'total':                 MODE_NUMBER,
    'status':                {**MODE_SELECT, 'options': ORDER_STATUS},
}


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


bp = Blueprint("orders", __name__)


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

    return render_template("sys_orders/dashboard.html", grupos=grupos_ordenados, hoje=hoje,
                           ORDER_STATUS=ORDER_STATUS, QUOTE_STATUS=QUOTE_STATUS)


@bp.route("/pedidos", endpoint="list")
def order_list():
    active = resolve_filters(ORDERS_FILTERS, request.args)
    q = (
        Order.query
        .options(
            db.joinedload(Order.conta),
            db.joinedload(Order.carteira),
        )
        .order_by(Order.data_entrega)
    )
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
    ctx = build_field_context(ORDERS_FIELDS, filters_config=ORDERS_FILTERS)
    return render_template("sys_orders/list.html", orders=orders, ORDERS_TABLE=ORDERS_TABLE, ctx=ctx, ORDER_STATUS=ORDER_STATUS, FORMINHAS=FORMINHAS, active_filters=active, FILTERS=ORDERS_FILTERS)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        client_id = request.form["client_id"]
        data_pedido_str = request.form.get("data_pedido")
        data_pedido = (
            datetime.strptime(data_pedido_str, "%Y-%m-%dT%H:%M")
            if data_pedido_str else datetime.now()
        )
        data_entrega_str = request.form.get("data_entrega")
        data_entrega = (
            datetime.strptime(data_entrega_str, "%Y-%m-%dT%H:%M")
            if data_entrega_str else None
        )
        data_previsao_entrega_str = request.form.get("data_previsao_entrega")
        data_previsao_entrega = (
            datetime.strptime(data_previsao_entrega_str, "%Y-%m-%dT%H:%M")
            if data_previsao_entrega_str else None
        )
        observacao = request.form.get("observacao", "")

        order = Order(
            client_id=client_id,
            data_pedido=data_pedido,
            data_previsao_entrega=data_previsao_entrega,
            data_entrega=data_entrega,
            observacao=observacao,
            carteira_id=request.form.get("carteira_id", type=int) or None,
            forminhas=request.form.get("forminhas", 0, type=int),
            status=9 if data_entrega else 0,
        )
        db.session.add(order)
        db.session.flush()
        _save_event(order, request.form)

        total = _replace_order_items(order, request.form)
        order.total = total

        db.session.commit()
        flash("Pedido criado!", "success")
        return redirect(url_for("orders.list"))

    clients = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([0, 1])).order_by(Conta.nome).all()
    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    carteiras = Carteira.query.filter(Carteira.uso.in_([0, 1])).order_by(Carteira.nome).all()
    return render_template(
        "sys_orders/form.html", order=None, clients=clients, products=products,
        ORDER_STATUS=ORDER_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
    )


@bp.route("/pedidos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    order = Order.query.get(id)
    if not order:
        flash("Código inexistente", "warning")
        return redirect(url_for("orders.list"))
    if request.method == "POST":
        if order.status == 9:
            data_entrega_str = request.form.get("data_entrega")
            if data_entrega_str:
                flash("Pedido entregue não pode ser alterado.", "warning")
            else:
                order.data_entrega = None
                order.status = 2
                db.session.commit()
                flash("Data de entrega removida. Pedido reaberto como Pronto.", "success")
            return redirect(url_for("orders.edit", id=id))

        order.client_id = request.form["client_id"]
        data_pedido_str = request.form.get("data_pedido")
        if data_pedido_str:
            order.data_pedido = datetime.strptime(data_pedido_str, "%Y-%m-%dT%H:%M")
        data_entrega_str = request.form.get("data_entrega")
        if data_entrega_str:
            order.data_entrega = datetime.strptime(data_entrega_str, "%Y-%m-%dT%H:%M")
            order.status = 9
        else:
            order.data_entrega = None
            order.status = int(request.form.get("status", order.status))
            if order.status == 0:
                order.status = 1
        data_previsao_entrega_str = request.form.get("data_previsao_entrega")
        order.data_previsao_entrega = (
            datetime.strptime(data_previsao_entrega_str, "%Y-%m-%dT%H:%M")
            if data_previsao_entrega_str else None
        )
        order.observacao = request.form.get("observacao", "")
        order.carteira_id = request.form.get("carteira_id", type=int) or None
        order.forminhas = request.form.get("forminhas", 0, type=int)
        _save_event(order, request.form)

        total = _replace_order_items(order, request.form)
        order.total = total

        db.session.flush()

        # Backfill quote_id if linked via pedido_id
        if not order.quote_id:
            quote = Quote.query.filter_by(pedido_id=order.id).first()
            if quote:
                order.quote_id = quote.id

        db.session.commit()
        if request.form.get("atualizar_precos"):
            flash("Preços zerados foram atualizados!", "success")
        else:
            flash("Pedido atualizado!", "success")
        return redirect(url_for("orders.edit", id=id))

    # Backfill quote_id on load if missing
    if not order.quote_id:
        q = Quote.query.filter_by(pedido_id=order.id).first()
        if q:
            order.quote_id = q.id
            db.session.commit()

    clients = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([0, 1])).order_by(Conta.nome).all()
    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()

    query = Order.query.with_entities(Order.id).order_by(Order.id)
    ids = [o.id for o in query.all()]
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

    carteiras = Carteira.query.filter(Carteira.uso.in_([0, 1])).order_by(Carteira.nome).all()
    return render_template(
        "sys_orders/form.html", order=order, clients=clients, products=products, nav=nav,
        ORDER_STATUS=ORDER_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
        PREVISAO_STATUS=PREVISAO_STATUS,
        ro=order.status == 9
    )


@bp.route("/pedidos/<int:id>/status", methods=["POST"])
def status(id):
    order = Order.query.get_or_404(id)
    if order.status == 9:
        flash("Pedido entregue não pode ter status alterado.", "warning")
        return redirect(url_for("orders.edit", id=id))
    novo_status = request.form["status"]
    if novo_status == "9" and not order.data_entrega:
        flash("Status Entregue só pode ser definido preenchendo a data de entrega.", "warning")
        return redirect(url_for("orders.edit", id=id))
    if novo_status in ("0", "1", "2", "8", "9"):
        order.status = int(novo_status)
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("orders.edit", id=id))


@bp.route("/pedidos/<int:id>/cancelar", methods=["POST"])
def cancel(id):
    order = Order.query.get_or_404(id)
    if order.status == 9:
        flash("Pedido entregue não pode ser cancelado.", "warning")
        return redirect(url_for("orders.edit", id=id))
    order.status = 3
    if order.transacao:
        order.transacao.cancelado = date.today()
    db.session.commit()
    flash("Pedido cancelado!", "success")
    return redirect(url_for("orders.edit", id=id))


@bp.route("/pedidos/<int:id>/print")
def print_order(id):
    order = Order.query.get_or_404(id)
    from app.reports.rep_pedido import PEDIDO_REPORT
    return render_template(
        PEDIDO_REPORT.print_template,
        fallback_url=url_for(PEDIDO_REPORT.edit_endpoint, id=order.id),
        pdf_url=url_for('orders.pdf_order', id=order.id),
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
        return redirect(url_for("orders.edit", id=id))

    fp = order.carteira
    if not fp:
        flash("Selecione uma forma de pagamento antes de gerar o financeiro.", "warning")
        return redirect(url_for("orders.edit", id=id))

    total = float(order.total or 0)
    taxa = float(fp.taxa_recebimento or 0)
    valor_liquido = round(total * (1 - taxa / 100), 2)

    if request.method == "POST":
        if fp.gerar == 0:
            recurso_id = request.form.get("recurso_id", type=int)
            if not recurso_id:
                flash("Selecione um recurso.", "warning")
                return redirect(url_for("orders.gerar_financeiro", id=id))
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
        return redirect(url_for("orders.edit", id=id))

    recursos = Recurso.query.order_by(Recurso.nome).all()
    parcelas = []
    if fp.gerar == 1:
        parcelas = parse_prazo_recebimento(
            fp.prazo_recebimento,
            order.data_pedido.date(),
            order.data_entrega.date() if order.data_entrega else None,
            total,
        )

    return render_template(
        "sys_orders/gerar_financeiro.html",
        order=order, fp=fp, recursos=recursos,
        total=total, taxa=taxa, valor_liquido=valor_liquido,
        parcelas=parcelas,
    )
