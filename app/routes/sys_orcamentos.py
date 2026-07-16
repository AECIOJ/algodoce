from datetime import date, datetime, timezone, timedelta
from io import BytesIO
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app
from flask_login import login_required
from app.extensions import db
from app.utils import parse_brl, _clean, _save_event
from app.models.client import Conta
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.event import Event
from app.models.carteira import Carteira
from app.constants import QUOTE_STATUS, QUOTE_STATUS_FILTER, FORMINHAS
from app.table import Field, build_field_context, Table
from app.pdf import gerar_pdf_orcamento, gerar_pdf_relatorio
from app.reports.orcamento import ORCAMENTO_REPORT
from app.filters import resolve_filters, apply_text_filter, apply_number_filter, apply_select_filter, apply_date_filter, build_fk_options, MODE_NUMBER, MODE_TEXT, MODE_DATE, MODE_SELECT


def quote_validade(item):
    ref = item.data_renovacao or item.data_pedido
    dias = item.validade or 3
    return (ref.replace(tzinfo=None) + timedelta(days=dias)).strftime('%d/%m/%Y')


QUOTES_FIELDS = [
    Field(name='id', label='#', width=7, mask='999.999'),
    Field(name='cliente_nome', label='Cliente', width=20, pos=1),
    Field(name='cliente_telefone', label='Telefone', width=16),
    Field(name='data_pedido', label='Data', width=10, input='date'),
    Field(name='validade', label='Validade', width=14, input='number', function=quote_validade),
    Field(name='total', label='Total', width=12, input='number', align='right', aggregate='sum', currency='brl'),
    Field(name='carteira', label='Pagamento', width=15, query='carteira'),
    Field(name='status', label='Status', width=14, options=QUOTE_STATUS, filter_options=QUOTE_STATUS),
    Field(name='pedido_id', label='Pedido', width=10, filter=False, link='orders.edit'),
]

QUOTES_TABLE = Table(fields=QUOTES_FIELDS, edit_endpoint='orcamentos.edit')

QUOTES_FILTERS = {
    'id':              MODE_NUMBER,
    'cliente_nome':    MODE_TEXT,
    'cliente_telefone': MODE_TEXT,
    'data_pedido':     MODE_DATE,
    'validade':        MODE_NUMBER,
    'total':           MODE_NUMBER,
    'carteira':        {**MODE_SELECT, 'filter_path': 'carteira.nome'},
    'status':          {**MODE_SELECT, 'options': QUOTE_STATUS},
}


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


bp = Blueprint("orcamentos", __name__)


@bp.before_request
@login_required
def protect():
    pass


@bp.route("/orcamentos", endpoint="list")
def orcamento_list():
    active = resolve_filters(QUOTES_FILTERS, request.args)
    query = Quote.query.order_by(Quote.id.desc())
    quotes = query.all()
    linhas = quotes[:]
    linhas = apply_select_filter(linhas, 'status', active.get('status'), QUOTE_STATUS)
    linhas = apply_number_filter(linhas, 'id', active.get('id'))
    linhas = apply_text_filter(linhas, 'cliente_nome', active.get('cliente_nome'))
    linhas = apply_text_filter(linhas, 'cliente_telefone', active.get('cliente_telefone'))
    linhas = apply_date_filter(linhas, 'data_pedido', active.get('data_pedido'))
    linhas = apply_number_filter(linhas, 'validade', active.get('validade'))
    linhas = apply_number_filter(linhas, 'total', active.get('total'))
    linhas = apply_select_filter(linhas, 'carteira', active.get('carteira'), build_fk_options(Carteira), filter_path='carteira.nome')
    quotes = linhas
    ctx = build_field_context(QUOTES_FIELDS, filters_config=QUOTES_FILTERS)
    return render_template(
        "sys_orcamentos/list.html", orders=quotes, QUOTES_TABLE=QUOTES_TABLE, ctx=ctx,
        filtro=active.get('status', 'todos'),
        QUOTE_STATUS=QUOTE_STATUS, QUOTE_STATUS_FILTER=QUOTE_STATUS_FILTER,
        active_filters=active, FILTERS=QUOTES_FILTERS,
    )


@bp.route("/orcamentos/<int:id>")
def detail(id):
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

    return render_template("sys_orcamentos/detail.html", quote=quote, nav=nav,
                           QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
                           perfect_match=perfect_match)


@bp.route("/orcamentos/<int:id>/converter", methods=["POST"])
def converter(id):
    quote = Quote.query.get(id)
    if not quote:
        flash("Código inexistente", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou reprovado.", "warning")
        return redirect(url_for("orcamentos.list"))

    tipo = request.form.get("converter_tipo", "existente")

    if tipo == "nova":
        nome = request.form.get("novo_nome", "").strip()
        telefone = request.form.get("novo_telefone", "").strip()
        if not nome:
            flash("Informe o nome da nova conta.", "warning")
            return redirect(url_for("orcamentos.edit", id=id))
        existing = Conta.query.filter(Conta.nome.ilike(nome)).first()
        if existing:
            flash(f"Já existe uma conta com o nome '{existing.nome}'. Selecione-a na lista de contas existentes.", "warning")
            return redirect(url_for("orcamentos.edit", id=id))
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
            return redirect(url_for("orcamentos.edit", id=id))
    else:
        client_id = request.form.get("client_id", type=int)
        conta = Conta.query.get(client_id)
        if not conta:
            flash("Selecione um cliente para converter.", "warning")
            return redirect(url_for("orcamentos.edit", id=id))

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
    return redirect(url_for("orcamentos.list"))


@bp.route("/orcamentos/<int:id>/editar", methods=["GET", "POST"])
def edit(id):
    quote = Quote.query.get(id)
    if not quote:
        flash("Código inexistente", "warning")
        return redirect(url_for("orcamentos.list"))

    if request.method == "POST":
        if quote.pedido_id:
            flash("Orçamento não pode ser alterado — já foi convertido em pedido.", "warning")
            return redirect(url_for("orcamentos.edit", id=id))

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
        return redirect(url_for("orcamentos.edit", id=id))

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
        "sys_orcamentos/form.html", quote=quote, products=products, nav=nav,
        tipos_evento=tipos_evento, clients=clients,
        QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
        ro=bool(quote.pedido_id),
        perfect_match=perfect_match,
        suggested_client=suggested_client,
        phone_conflict=phone_conflict,
    )


@bp.route("/orcamentos/novo", methods=["GET", "POST"])
def new():
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
        return redirect(url_for("orcamentos.edit", id=quote.id))

    products = Product.query.filter_by(ativo=True).order_by(Product.nome).all()
    tipos_evento = [
        "Aniversário", "Casamento", "Debutante", "Corporativo",
        "Infantil", "Família", "Confraternização", "Religioso", "Outros"
    ]
    clients = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    carteiras = Carteira.query.order_by(Carteira.nome).all()
    return render_template(
        "sys_orcamentos/form.html", quote=None, products=products,
        tipos_evento=tipos_evento, clients=clients,
        QUOTE_STATUS=QUOTE_STATUS, FORMINHAS=FORMINHAS,
        carteiras=carteiras,
    )


@bp.route("/orcamentos/<int:id>/status", methods=["POST"])
def status(id):
    quote = Quote.query.get_or_404(id)
    novo_status = request.form["status"]
    if novo_status in ("0", "1", "6", "7", "8", "9"):
        quote.status = int(novo_status)
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("orcamentos.edit", id=id))


@bp.route("/orcamentos/validar")
def validar():
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
    return redirect(url_for("orcamentos.list"))


@bp.route("/orcamentos/<int:id>/renovar", methods=["POST"])
def renovar(id):
    quote = Quote.query.get_or_404(id)
    if quote.status != 7:
        flash("Apenas orçamentos expirados podem ser renovados.", "warning")
        return redirect(url_for("orcamentos.list"))
    hoje = datetime.utcnow()
    quote.data_renovacao = hoje
    quote.status = 6
    db.session.commit()
    flash("Orçamento renovado com sucesso!", "success")
    return redirect(url_for("orcamentos.edit", id=id))


@bp.route("/orcamentos/<int:id>/excluir", methods=["POST"])
def excluir(id):
    quote = Quote.query.get_or_404(id)
    for item in list(quote.items):
        db.session.delete(item)
    db.session.delete(quote)
    db.session.commit()
    flash("Orçamento excluído!", "success")
    return redirect(url_for("orcamentos.list"))


@bp.route("/orcamentos/<int:id>/print")
def print_quote(id):
    quote = Quote.query.get_or_404(id)
    return render_template("sys_orcamentos/print.html", quote=quote, FORMINHAS=FORMINHAS)


@bp.route("/orcamentos/<int:id>/pdf")
def pdf_quote(id):
    quote = Quote.query.get_or_404(id)
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(ORCAMENTO_REPORT, quote.items, logo_path, instance=quote)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=orcamento_{quote.id}.pdf"})
