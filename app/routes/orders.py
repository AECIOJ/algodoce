from datetime import date, datetime, timezone
from io import BytesIO
from app.utils import parse_brl, parse_prazo_recebimento
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from flask_login import login_required
import os
from sqlalchemy import func
from app.extensions import db
from app.models.client import Conta
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote_item import QuoteItem
from app.models.event import Event
from app.models.quote import Quote
from app.pdf import gerar_pdf_pedido, gerar_pdf_orcamento
from app.models.carteira import Carteira
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.constants import ORDER_STATUS, QUOTE_STATUS, QUOTE_STATUS_FILTER, FORMINHAS, PREVISAO_STATUS
from app.fields import Field, build_field_context


ORDERS_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='cliente', label='Cliente', width=20, query='conta'),
    Field(name='data_pedido', label='Data Pedido', width=10, input='date'),
    Field(name='data_previsao_entrega', label='Prev. Entrega', width=10, input='date'),
    Field(name='data_entrega', label='Data Entrega', width=10, input='date'),
    Field(name='forminhas', label='Forminhas', width=12, filter_options=list(FORMINHAS.values())),
    Field(name='carteira', label='Pagamento', width=15, query='carteira'),
    Field(name='total', label='Total', width=10, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='status', label='Status', width=12, filter_options=list(ORDER_STATUS.values())),
    Field(name='transacao', label='Faturado', width=10, filter=False),
    Field(name='quote_id', label='Orçamento', width=9, filter=False),
]

QUOTES_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='cliente_nome', label='Cliente', width=20),
    Field(name='cliente_telefone', label='Telefone', width=16),
    Field(name='data_pedido', label='Data', width=10, input='date'),
    Field(name='validade', label='Validade', width=10, input='number'),
    Field(name='total', label='Total', width=12, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='carteira', label='Pagamento', width=15, query='carteira'),
    Field(name='status', label='Status', width=14, filter_options=list(QUOTE_STATUS.values())),
    Field(name='pedido_id', label='Pedido', width=10, filter=False),
]


def _clean(val):
    if not val:
        return None
    s = val.strip()
    if not s or s.lower() == "none":
        return None
    return s


def _save_event(obj, form):
    if not obj.event:
        event = Event()
        obj.event = event
        db.session.add(event)
        db.session.flush()
    event = obj.event
    event.tipo = _clean(form.get("evento_tipo"))
    event.tema = _clean(form.get("evento_tema"))
    event.obs = _clean(form.get("evento_complemento"))
    data_str = form.get("evento_data")
    event.data = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else None
    hora_str = form.get("evento_hora")
    event.hora = datetime.strptime(hora_str, "%H:%M").time() if hora_str else None
    event.local = _clean(form.get("evento_local"))
    conv_str = form.get("evento_convidados")
    event.convidados = int(conv_str) if conv_str else None
    event.cerimonial = _clean(form.get("evento_cerimonial"))
    return event


def _replace_quote_items(quote, form):
    for item in list(quote.items):
        db.session.delete(item)

    produtos = form.getlist("product_id")
    quantidades = form.getlist("quantidade")
    precos = form.getlist("preco_unitario")
    obs_itens = form.getlist("observacao_item")
    total = 0
    for pid, qtd, prc, obs in zip(produtos, quantidades, precos, obs_itens):
        if not pid or not qtd:
            continue
        qtd_val = int(qtd)
        prc_val = parse_brl(prc)
        item = QuoteItem(
            quote_id=quote.id, product_id=int(pid),
            quantidade=qtd_val, preco_unitario=prc_val,
            observacao=_clean(obs),
        )
        db.session.add(item)
        if prc_val:
            total += prc_val * qtd_val
    return total


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

    return render_template("orders/dashboard.html", grupos=grupos_ordenados, hoje=hoje,
                           ORDER_STATUS=ORDER_STATUS, QUOTE_STATUS=QUOTE_STATUS)


@bp.route("/pedidos", endpoint="list")
def order_list():
    orders = (
        Order.query
        .options(
            db.joinedload(Order.conta),
            db.joinedload(Order.carteira),
        )
        .order_by(Order.data_entrega)
        .all()
    )
    ctx = build_field_context(ORDERS_FIELDS)
    return render_template("orders/list.html", orders=orders, fields=ORDERS_FIELDS, ctx=ctx, ORDER_STATUS=ORDER_STATUS, FORMINHAS=FORMINHAS)


@bp.route("/orcamentos")
def orcamentos():
    status = request.args.get("status", type=int)
    query = Quote.query.order_by(Quote.id.desc())
    if status is not None:
        query = query.filter(Quote.status == status)
    quotes = query.all()
    ctx = build_field_context(QUOTES_FIELDS)
    return render_template(
        "orders/orcamentos.html", orders=quotes, fields=QUOTES_FIELDS, ctx=ctx,
        filtro=str(status) if status is not None else "todos",
        QUOTE_STATUS=QUOTE_STATUS, QUOTE_STATUS_FILTER=QUOTE_STATUS_FILTER,
    )


@bp.route("/orcamentos/<int:id>")
def quote_detail(id):
    quote = Quote.query.get_or_404(id)

    perfect_match = None
    if quote.cliente_nome:
        perfect_match = Conta.query.filter(
            Conta.nome.ilike(quote.cliente_nome),
            Conta.telefone == quote.cliente_telefone,
        ).first()

    query = Quote.query.with_entities(Quote.id).order_by(Quote.id)
    ids = [q.id for q in query.all()]
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

    return render_template("orders/quote_detail.html", quote=quote, nav=nav,
                           QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
                           perfect_match=perfect_match)


@bp.route("/orcamentos/<int:id>/converter", methods=["POST"])
def converter_orcamento(id):
    quote = Quote.query.get(id)
    if not quote:
        flash("Código inexistente", "warning")
        return redirect(url_for("orders.orcamentos"))
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orders.orcamentos"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou reprovado.", "warning")
        return redirect(url_for("orders.orcamentos"))

    tipo = request.form.get("converter_tipo", "existente")

    if tipo == "nova":
        nome = request.form.get("novo_nome", "").strip()
        telefone = request.form.get("novo_telefone", "").strip()
        if not nome:
            flash("Informe o nome da nova conta.", "warning")
            return redirect(url_for("orders.quote_edit", id=id))
        existing = Conta.query.filter(Conta.nome.ilike(nome)).first()
        if existing:
            flash(f"Já existe uma conta com o nome '{existing.nome}'. Selecione-a na lista de contas existentes.", "warning")
            return redirect(url_for("orders.quote_edit", id=id))
        conta = Conta(
            nome=nome,
            telefone=telefone or None,
            email=None,
            tipo=0,
        )
        db.session.add(conta)
        db.session.flush()
    elif tipo == "auto":
        client_id = request.form.get("client_id", type=int)
        conta = Conta.query.get(client_id)
        if not conta:
            flash("Conta não encontrada para conversão automática.", "warning")
            return redirect(url_for("orders.quote_edit", id=id))
    else:
        client_id = request.form.get("client_id", type=int)
        conta = Conta.query.get(client_id)
        if not conta:
            flash("Selecione um cliente para converter.", "warning")
            return redirect(url_for("orders.quote_edit", id=id))

    order = Order(
        client_id=conta.id,
        data_entrega=None,
        observacao=quote.observacao,
        carteira_id=quote.carteira_id,
        forminhas=quote.forminhas,
        status=0,
    )
    db.session.add(order)
    db.session.flush()

    # Copy quote items as order items
    for item in quote.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            observacao=item.observacao,
        )
        db.session.add(order_item)

    db.session.flush()
    order.total = sum(
        (i.preco_unitario or 0) * i.quantidade for i in order.items
    )
    if quote.event:
        order.event = quote.event
    quote.status = 9
    quote.pedido_id = order.id
    order.quote_id = quote.id

    db.session.commit()
    flash("Orçamento convertido para pedido!", "success")
    return redirect(url_for("orders.orcamentos"))


@bp.route("/orcamentos/<int:id>/editar", methods=["GET", "POST"])
def quote_edit(id):
    quote = Quote.query.get(id)
    if not quote:
        flash("Código inexistente", "warning")
        return redirect(url_for("orders.orcamentos"))

    if request.method == "POST":
        if quote.pedido_id:
            flash("Orçamento não pode ser alterado — já foi convertido em pedido.", "warning")
            return redirect(url_for("orders.quote_edit", id=id))

        quote.cliente_nome = request.form["cliente_nome"]
        quote.cliente_telefone = request.form["cliente_telefone"]
        quote.status = int(request.form.get("status", 0))
        if quote.status == 0:
            quote.status = 1
        quote.observacao = _clean(request.form.get("observacao"))
        quote.validade = request.form.get("validade", 3, type=int)
        quote.carteira_id = request.form.get("carteira_id", type=int) or None
        quote.forminhas = request.form.get("forminhas", 0, type=int)

        _save_event(quote, request.form)

        total = _replace_quote_items(quote, request.form)
        quote.total = total
        db.session.flush()

        db.session.commit()
        if request.form.get("atualizar_precos"):
            flash("Preços zerados foram atualizados!", "success")
        else:
            flash("Orçamento atualizado!", "success")
        return redirect(url_for("orders.quote_edit", id=id))

    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    tipos_evento = [
        "Aniversário", "Casamento", "Debutante", "Corporativo",
        "Infantil", "Família", "Confraternização", "Religioso", "Outros"
    ]
    # Backfill order.quote_id on load if missing
    if quote.pedido_id:
        order = Order.query.get(quote.pedido_id)
        if order and not order.quote_id:
            order.quote_id = quote.id
            db.session.commit()

    clients = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()

    perfect_match = None
    suggested_client = None
    phone_conflict = None
    if quote.cliente_nome:
        perfect_match = Conta.query.filter(
            Conta.nome.ilike(quote.cliente_nome),
            Conta.telefone == quote.cliente_telefone,
        ).first()
    if not perfect_match:
        if quote.cliente_nome:
            suggested_client = Conta.query.filter(Conta.nome.ilike(quote.cliente_nome)).first()
        if not suggested_client and quote.cliente_telefone:
            suggested_client = Conta.query.filter(Conta.telefone == quote.cliente_telefone).first()
        if quote.cliente_telefone:
            phone_owner = Conta.query.filter(
                Conta.telefone == quote.cliente_telefone,
            ).first()
            if phone_owner and (
                not suggested_client or phone_owner.id != suggested_client.id
            ):
                phone_conflict = phone_owner

    query = Quote.query.with_entities(Quote.id).order_by(Quote.id)
    ids = [q.id for q in query.all()]
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

    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "orders/quote_form.html", quote=quote, products=products, nav=nav,
        tipos_evento=tipos_evento, clients=clients,
        QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
        ro=bool(quote.pedido_id),
        perfect_match=perfect_match,
        suggested_client=suggested_client,
        phone_conflict=phone_conflict,
    )


@bp.route("/orcamentos/novo", methods=["GET", "POST"])
def quote_new():
    if request.method == "POST":
        cliente_nome = request.form["cliente_nome"]
        cliente_telefone = request.form["cliente_telefone"]

        quote = Quote(
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            data_pedido=datetime.now(timezone.utc),
            status=0,
            validade=request.form.get("validade", 3, type=int),
            carteira_id=request.form.get("carteira_id", type=int) or None,
        )
        db.session.add(quote)
        db.session.flush()

        produtos = request.form.getlist("product_id")
        quantidades = request.form.getlist("quantidade")
        precos = request.form.getlist("preco_unitario")
        obs_itens = request.form.getlist("observacao_item")
        total = 0
        for pid, qtd, prc, obs in zip(produtos, quantidades, precos, obs_itens):
            if not pid or not qtd:
                continue
            qtd_val = int(qtd)
            prc_val = parse_brl(prc)
            item = QuoteItem(
                quote_id=quote.id, product_id=int(pid),
                quantidade=qtd_val, preco_unitario=prc_val,
                observacao=_clean(obs),
            )
            db.session.add(item)
            if prc_val:
                total += prc_val * qtd_val

        quote.total = total
        db.session.commit()
        flash("Orçamento criado!", "success")
        return redirect(url_for("orders.quote_edit", id=quote.id))

    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    tipos_evento = [
        "Aniversário", "Casamento", "Debutante", "Corporativo",
        "Infantil", "Família", "Confraternização", "Religioso", "Outros"
    ]
    clients = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "orders/quote_form.html", quote=None, products=products,
        tipos_evento=tipos_evento, clients=clients,
        QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
    )


@bp.route("/orcamentos/<int:id>/status", methods=["POST"])
def quote_status(id):
    quote = Quote.query.get_or_404(id)
    novo_status = request.form["status"]
    if novo_status in ("0", "1", "6", "7", "8", "9"):
        quote.status = int(novo_status)
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("orders.quote_edit", id=id))


@bp.route("/orcamentos/validar")
def quote_validar():
    hoje = datetime.utcnow()
    expirados = 0
    quotes = Quote.query.filter(Quote.status < 7).all()
    for q in quotes:
        ref = q.data_renovacao or q.data_pedido
        dias = (hoje - ref).days
        if dias > (q.validade or 3):
            q.status = 7
            expirados += 1
    db.session.commit()
    flash(f"{expirados} orçamento(s) expirado(s) automaticamente.", "info")
    return redirect(url_for("orders.orcamentos"))


@bp.route("/orcamentos/<int:id>/renovar", methods=["POST"])
def quote_renovar(id):
    quote = Quote.query.get_or_404(id)
    if quote.status != 7:
        flash("Apenas orçamentos expirados podem ser renovados.", "warning")
        return redirect(url_for("orders.orcamentos"))
    hoje = datetime.utcnow()
    quote.data_renovacao = hoje
    quote.status = 6
    db.session.commit()
    flash("Orçamento renovado com sucesso!", "success")
    return redirect(url_for("orders.quote_edit", id=id))


@bp.route("/orcamentos/<int:id>/excluir", methods=["POST"])
def quote_delete(id):
    quote = Quote.query.get_or_404(id)
    for item in list(quote.items):
        db.session.delete(item)
    db.session.delete(quote)
    db.session.commit()
    flash("Orçamento excluído!", "success")
    return redirect(url_for("orders.orcamentos"))


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
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "orders/form.html", order=None, clients=clients, products=products,
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

    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "orders/form.html", order=order, clients=clients, products=products, nav=nav,
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
    return render_template("orders/print_order.html", order=order, FORMINHAS=FORMINHAS)


@bp.route("/orcamentos/<int:id>/print")
def print_quote(id):
    quote = Quote.query.get_or_404(id)
    return render_template("orders/print_quote.html", quote=quote, FORMINHAS=FORMINHAS)


@bp.route("/pedidos/<int:id>/pdf")
def pdf_order(id):
    order = Order.query.get_or_404(id)
    logo_path = os.path.join(current_app.root_path, "static", "imagens", "Logo.png")
    pdf = gerar_pdf_pedido(order, logo_path)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=pedido_{order.id}.pdf"})


@bp.route("/orcamentos/<int:id>/pdf")
def pdf_quote(id):
    quote = Quote.query.get_or_404(id)
    logo_path = os.path.join(current_app.root_path, "static", "imagens", "Logo.png")
    pdf = gerar_pdf_orcamento(quote, logo_path)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=orcamento_{quote.id}.pdf"})


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
        "orders/gerar_financeiro.html",
        order=order, fp=fp, recursos=recursos,
        total=total, taxa=taxa, valor_liquido=valor_liquido,
        parcelas=parcelas,
    )
