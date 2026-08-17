from datetime import datetime, timezone, timedelta
from io import BytesIO
import os
from flask import request, redirect, url_for, flash, Response, render_template, current_app
from app.ajsystem.core.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.constantes import QUOTE_STATUS, FORMINHAS
from app.ajsystem.core import auto
from app.ajsystem.core.do_list import do_list
from app.ajsystem.core.form import pesquise
from app.ajsystem.core.pdf import gerar_pdf_relatorio
from app.reports import ORCAMENTO_REPORT


def quote_validade(item):
    ref = item.data_renovacao or item.data_pedido
    dias = item.validade or 3
    return (ref.replace(tzinfo=None) + timedelta(days=dias)).strftime('%d/%m/%Y')


def preco_on_set(row):
    """`on_set` do produto: preenche o preço unitário a partir da tabela de
    produtos (pesquise) apenas quando o preço ainda não foi informado — nunca
    sobrescreve valor digitado/gravado. Executado só na intervenção do operador
    (via `/api/on_set`), nunca no save."""
    if row.get('preco_unitario'):
        return
    try:
        pid = int(row.get('product_id'))
    except (TypeError, ValueError):
        return
    valor = pesquise('product', pid, 'preco')
    if valor is None:
        return
    divisor = pesquise('product', pid, 'qtd_minima') or 1
    try:
        row['preco_unitario'] = float(valor) / float(divisor)
    except (TypeError, ValueError, ZeroDivisionError):
        return


tipos_evento_list = [
    "Infantil", "Família", "Confraternização", "Religioso", "Outros"
]
tipos_evento = {t: t for t in tipos_evento_list}


Entity = {
    'Quote': {
        'id':               {'type': 'ID', 'width': 6},
        'cliente_nome':     {'label': 'Cliente', 'required': True, 'width': 20},
        'cliente_telefone': {'label': 'Telefone', 'required': True, 'width': 16, 'mask': '(99) 99999-9999'},
        'data_pedido':      {'label': 'Data', 'input': 'date', 'width': 10},
        'validade':         {'label': 'Validade (dias)', 'input': 'number', 'width': 14, 'attrs': {'min': 1}, 'card_path': 'validade_data', 'filter': False},
        'forminhas':        {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
        'total':            {'type': 'NUM', 'currency': 'brl', 'aggregate': {'table': 'items', 'sum': 'preco_unitario * quantidade'}, 'width': 12},
        'carteira_id':      {'type': 'FK', 'label': 'Pagamento', 'query': 'carteira', 'query_filter': {'uso': [0, 1]}, 'width': 15, 'filter': False, 'card_path': 'carteira.nome'},
        'observacao':       {'label': 'Observação', 'input': 'textarea', 'width': 12},
        'status':           {'type': 'LIST', 'width': 12, 'options': QUOTE_STATUS, 'filter_options': QUOTE_STATUS},
        'pedido_id':        {'label': 'Pedido', 'width': 9, 'filter': False, 'link': 'pedidos.form'},
    },
    'QuoteItem': {
        '__meta__':         {'label': 'Itens do Orçamento'},
        'id':               {'type': 'ID'},
        'quote_id':         {'type': 'ID'},
        'product_id':       {'type': 'FK', 'label': 'Produto', 'required': True, 'on_set': preco_on_set},
        'quantidade':       {'type': 'INT', 'label': 'Qtd', 'required': True},
        'preco_unitario':   {'type': 'NUM', 'label': 'Preço', 'currency': 'brl'},
        'valor':            {'type': 'NUM', 'label': 'Valor', 'currency': 'brl', 'in_form': False, 'calc': 'quantidade * preco_unitario'},
        'observacao':       {'type': 'TEXT', 'label': 'Obs', 'required': False},
    },
    'Event': {
        '__meta__':   {'label': 'Evento'},
        'id':         {'type': 'ID'},
        'quote_id':   {'type': 'ID'},
        'order_id':   {'type': 'ID', 'in_form': False},
        'tipo':       {'type': 'LIST', 'label': 'Tipo', 'options': tipos_evento},
        'tema':       {'type': 'TEXT', 'label': 'Tema'},
        'convidados': {'type': 'INT', 'label': 'Nº Convidados'},
        'obs':        {'type': 'MEMO', 'label': 'Observação'},
        'data':       {'type': 'DATA', 'label': 'Data'},
        'hora':       {'type': 'HORA', 'label': 'Hora'},
        'local':      {'type': 'TEXT', 'label': 'Local'},
        'cerimonial': {'type': 'TEXT', 'label': 'Cerimonial'},
    },
}

Page = {
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'fields': [
                'Quote.id', 'Quote.cliente_nome', 'Quote.cliente_telefone', 'Quote.data_pedido',
                'Quote.validade', 'Quote.total', 'Quote.carteira_id', 'Quote.status', 'Quote.pedido_id',
            ],
            'template': 'sys/orcamentos/list.html',
        },
        'form': {
            'readonly_when': {'pedido_id': lambda v: v is not None},
            'defaults': {'status': 1},
            'buttons': [
                {'label': 'Converter', 'icon': 'arrow-path', 'color': 'success', 'outline': False,
                 'endpoint': 'orcamentos.converter', 'position': 'nav_right',
                 'hide_if': ['pedido_id', None]},
            ],
            'delete': {
                'when': lambda q: q.pedido_id is None,
                'msg_ok': 'Orçamento excluído!',
                'msg_no': 'Exclua o pedido vinculado antes de excluir o orçamento.',
            },
            'fields': [
                'cliente_nome', 'cliente_telefone', 'validade', 'forminhas', 'carteira_id', 'observacao',
            ],
            'sessions': {
                'Itens do Orçamento': {'table': ['QuoteItem']},
                'Evento': {'table': ['Event']},
            },
        },
    },
}


def _converter_context(quote):
    """Clientes + sugestões para a página de conversão (saiu do modal/pre_get)."""
    clients = Conta.query.filter_by(ativo=True).order_by(Conta.nome).all()
    ctx = dict(clients=clients, perfect_match=None, suggested_client=None, phone_conflict=None)
    if not quote or not quote.cliente_nome:
        return ctx
    perfect = Conta.query.filter(
        Conta.nome.ilike(quote.cliente_nome),
        Conta.telefone == quote.cliente_telefone,
    ).first()
    ctx['perfect_match'] = perfect
    if perfect:
        return ctx
    suggested = Conta.query.filter(Conta.nome.ilike(quote.cliente_nome)).first()
    if not suggested and quote.cliente_telefone:
        suggested = Conta.query.filter(Conta.telefone == quote.cliente_telefone).first()
    if suggested:
        ctx['suggested_client'] = suggested
    if quote.cliente_telefone:
        phone_owner = Conta.query.filter(Conta.telefone == quote.cliente_telefone).first()
        if phone_owner and (not suggested or phone_owner.id != suggested.id):
            ctx['phone_conflict'] = phone_owner
    return ctx


@auto.rota('/', endpoint='list')
def list_orcamentos():
    quotes = Quote.query.order_by(Quote.id.desc()).all()
    for q in quotes:
        q.validade_data = quote_validade(q)
    return do_list('Quote', __name__, data=quotes)


@auto.rota('/<int:id>/converter', methods=['GET', 'POST'], endpoint='converter')
def converter(id):
    quote = Quote.query.get_or_404(id)
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou reprovado.", "warning")
        return redirect(url_for("orcamentos.list"))

    if request.method == "GET":
        return render_template(
            'sys/orcamentos/converter.html',
            quote=quote,
            total=quote.total,
            clientes=_converter_context(quote),
            QUOTE_STATUS=QUOTE_STATUS,
        )

    tipo = request.form.get("converter_tipo", "existente")

    if tipo == "nova":
        nome = request.form.get("novo_nome", "").strip()
        telefone = request.form.get("novo_telefone", "").strip()
        if not nome:
            flash("Informe o nome da nova conta.", "warning")
            return redirect(url_for("orcamentos.converter", id=id))
        existing = Conta.query.filter(Conta.nome.ilike(nome)).first()
        if existing:
            flash(f"Já existe uma conta com o nome '{existing.nome}'. Selecione-a na lista de contas existentes.", "warning")
            return redirect(url_for("orcamentos.converter", id=id))
        conta = Conta(
            nome=nome,
            telefone=telefone or None,
            email=None,
            tipo=0,
        )
        db.session.add(conta)
        db.session.flush()
    else:
        client_id = request.form.get("client_id", type=int)
        conta = Conta.query.get(client_id)
        if not conta:
            flash("Selecione um cliente para converter.", "warning")
            return redirect(url_for("orcamentos.converter", id=id))

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


@auto.rota('/<int:id>/status', methods=['POST'], endpoint='status')
def status(id):
    quote = Quote.query.get_or_404(id)
    novo_status = request.form["status"]
    if novo_status in ("0", "1", "6", "7", "8", "9"):
        quote.status = int(novo_status)
        db.session.commit()
        flash("Status atualizado!", "success")
    return redirect(url_for("orcamentos.form", id=id))


@auto.rota('/validar', endpoint='validar')
def validar():
    hoje = datetime.utcnow()
    expirados = 0
    quotes = Quote.query.filter(Quote.status < 7).all()
    for q in quotes:
        ref = q.data_renovacao or q.data_pedido
        dias = (hoje - ref.replace(tzinfo=None)).days
        if dias > (q.validade or 3):
            q.status = 7
            expirados += 1
    db.session.commit()
    flash(f"{expirados} orçamento(s) expirado(s) automaticamente.", "info")
    return redirect(url_for("orcamentos.list"))


@auto.rota('/<int:id>/renovar', methods=['POST', 'GET'], endpoint='renovar')
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
    return redirect(url_for("orcamentos.form", id=id))


@auto.rota('/<int:id>/excluir', methods=['POST'], endpoint='delete')
def excluir(id):
    quote = Quote.query.get_or_404(id)
    if quote.pedido_id:
        flash("Exclua o pedido vinculado antes de excluir o orçamento.", "danger")
        return redirect(url_for("orcamentos.form", id=id))
    for item in list(quote.items):
        db.session.delete(item)
    db.session.delete(quote)
    db.session.commit()
    flash("Orçamento excluído!", "success")
    return redirect(url_for("orcamentos.list"))


@auto.rota('/<int:id>/pdf', endpoint='pdf')
def pdf_quote(id):
    quote = Quote.query.get_or_404(id)
    if quote.pedido_id:
        return redirect(url_for('pedidos.pdf_order', id=quote.pedido_id))
    logo_path = os.path.join(current_app.root_path, "static", "icons", "Logo.png")
    pdf = gerar_pdf_relatorio(ORCAMENTO_REPORT, quote.items, logo_path, instance=quote)
    buf = BytesIO()
    pdf.output(buf)
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition": f"inline; filename=orcamento_{quote.id}.pdf"})
