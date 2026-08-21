from datetime import datetime, timezone, timedelta
from flask import request, redirect, url_for, flash, render_template
from app.ajsystem.core.extensions import db
from app.models.client import Conta
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.constantes import QUOTE_STATUS, FORMINHAS
from app.ajsystem.core import auto
from app.ajsystem.core.do_list import do_list
from app.ajsystem.core.do_report import print_report
from app.ajsystem.core.form import pesquise
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


def _btn_validar_action(_):
    """Botão Validar da listagem — valida orçamentos expirados."""
    return url_for('orcamentos.validar')


def _btn_converter_action(instance):
    """Botão Converter do form — abre a página de conversão do orçamento."""
    return url_for('orcamentos.converter', id=instance.id)


def _btn_enviar_action(instance):
    """Botão Enviar do form — pre-controle + impressão do orçamento."""
    if instance is None or not instance.items:
        return ''
    return print_report(ORCAMENTO_REPORT, instance)


def _btn_rejeitar_action(instance):
    """Botão Rejeitar do form — rejeita o orçamento."""
    return url_for('orcamentos.rejeitar', id=instance.id)


def _btn_atualizar_precos_action(instance):
    """Botão Atualizar preços zerados — busca preços dos produtos para itens com preço zero."""
    return url_for('orcamentos.atualizar_precos', id=instance.id)


def _orcamento_pre_save(instance, request, is_new):
    """Muda status de 0 (Pendente) para 1 (Negociação) na 1a edição admin."""
    if not is_new and instance.status == 0:
        instance.status = 1


Entity = {
    'Quote': {
        'id':               {'type': 'ID', 'width': 6},
        'cliente_nome':     {'label': 'Cliente', 'required': True, 'width': 20},
        'cliente_telefone': {'label': 'Telefone', 'required': True, 'mask': '(99) 99999-9999'},
        'data_pedido':      {'label': 'Data', 'input': 'date', 'in_form': 2},
        'data_renovacao':   {'label': 'Renovado em', 'input': 'date', 'in_form': 3, 'in_list': 0, 'in_filter': 0},
        'validade':         {'label': 'Validade (dias)', 'input': 'number', 'width': 14, 'min': 1, 'in_list': 0},
        'validade_data':    {'label': 'Válido até', 'calc': quote_validade, 'width': 14, 'in_form': 2, 'in_filter': 0},
        'forminhas':        {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12, 'in_list': 0},
        'total':            {'type': 'NUM', 'currency': 'brl', 'agg': {'table': 'items', 'sum': 'preco_unitario * quantidade'}, 'width': 12, 'in_form': 0},
        'carteira_id':      {'type': 'FK', 'label': 'Pagamento', 'query': {'model': 'carteira', 'when': 'uso IN (0, 1)'}, 'width': 15, 'in_filter': 0},
        'observacao':       {'label': 'Observação', 'input': 'textarea', 'in_list': 0},
        'status':           {'type': 'LIST', 'width': 12, 'options': QUOTE_STATUS, 'in_form': 0, 'in_filter': 3},
        'pedido_id':        {'label': 'Pedido', 'width': 9, 'in_form': 0, 'in_filter': 0, 'link': 'pedidos.form'},
    },
    'QuoteItem': {
        'id':               {'type': 'ID'},
        'quote_id':         {'type': 'DK'},
        'product_id':       {'type': 'FK', 'label': 'Produto', 'required': True, 'on_set': preco_on_set},
        'quantidade':       {'type': 'INT', 'label': 'Qtd', 'required': True},
        'preco_unitario':   {'type': 'NUM', 'label': 'Preço', 'currency': 'brl'},
        'valor':            {'type': 'NUM', 'label': 'Valor', 'currency': 'brl', 'in_form': 0, 'calc': 'quantidade * preco_unitario'},
        'observacao':       {'type': 'TEXT', 'label': 'Obs', 'required': False},
    },
    'Event': {
        'id':         {'type': 'ID'},
        'quote_id':   {'type': 'DK'},
        'order_id':   {'type': 'ID', 'in_form': 0},
        'tipo':       {'type': 'LIST', 'label': 'Tipo', 'options': tipos_evento},
        'tema':       {'type': 'TEXT', 'label': 'Tema'},
        'convidados': {'type': 'INT', 'label': 'Nº Convidados', 'width':10},
        'data':       {'type': 'DATA', 'label': 'Data'},
        'hora':       {'type': 'HORA', 'label': 'Hora'},
        'local':      {'type': 'TEXT', 'label': 'Local'},
        'cerimonial': {'type': 'TEXT', 'label': 'Cerimonial'},
        'obs':        {'type': 'MEMO', 'label': 'Observação'},
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
            'fields': 'Quote',
            'tags': [{'field': 'status', 'colors': {0: 'warning', 1: 'info', 6: 'info', 7: 'error', 8: 'error', 9: 'success'}}],
            'buttons': [
                {'label': 'Validar', 'icon': 'check', 'action': _btn_validar_action,
                 'color': 'info', 'outline': True},
            ],
        },
        'form': {
            'readonly_when': {'pedido_id': lambda v: v is not None},
            'defaults': {'status': 1},
            'pre_save': _orcamento_pre_save,
            'tags': [{'field': 'status', 'colors': {0: 'warning', 1: 'info', 6: 'info', 7: 'error', 8: 'error', 9: 'success'}}],
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success', 'outline': True,
                 'action': _btn_enviar_action, 'render': '#page-content', 'position': 'nav_right',
                 'when': lambda i: i.pedido_id is None and i.status < 7},
                {'label': 'Converter', 'icon': 'arrow-path', 'color': 'success', 'outline': False,
                 'action': _btn_converter_action, 'position': 'nav_right',
                 'when': lambda i: i.pedido_id is None and i.status < 7},
                {'label': 'Rejeitar', 'icon': 'xmark', 'color': 'error', 'outline': True,
                 'action': _btn_rejeitar_action, 'position': 'footer_left',
                 'when': lambda i: i.status < 7},
            ],
            'delete': {
                'when': lambda q: q.pedido_id is None,
                'msg_ok': 'Orçamento excluído!',
                'msg_no': 'Exclua o pedido vinculado antes de excluir o orçamento.',
            },
            'fields': 'Quote',
            'sessions': {
                'Itens do Orçamento': {
                    'table': ['QuoteItem'],
                    'buttons': [
                        {'label': 'Preços', 'icon': 'arrow-path',
                         'color': 'warning', 'outline': True,
                         'action': _btn_atualizar_precos_action},
                    ],
                },
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
    return do_list('Quote', __name__, data=quotes)


@auto.rota('/<int:id>/converter', methods=['GET', 'POST'], endpoint='converter')
def converter(id):
    quote = Quote.query.get_or_404(id)
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou rejeitado.", "warning")
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


@auto.rota('/<int:id>/rejeitar', methods=['POST', 'GET'], endpoint='rejeitar')
def rejeitar(id):
    quote = Quote.query.get_or_404(id)
    if quote.status >= 7:
        flash("Este orçamento já não pode ser rejeitado.", "warning")
        return redirect(url_for("orcamentos.form", id=id))
    quote.status = 8
    db.session.commit()
    flash("Orçamento rejeitado!", "success")
    return redirect(url_for("orcamentos.form", id=id))


@auto.rota('/<int:id>/atualizar-precos', methods=['POST', 'GET'], endpoint='atualizar_precos')
def atualizar_precos(id):
    quote = Quote.query.get_or_404(id)
    count = 0
    for item in quote.items:
        if item.preco_unitario:
            continue
        valor = pesquise('product', item.product_id, 'preco')
        if valor is None:
            continue
        divisor = pesquise('product', item.product_id, 'qtd_minima') or 1
        try:
            item.preco_unitario = float(valor) / float(divisor)
            count += 1
        except (TypeError, ValueError, ZeroDivisionError):
            continue
    db.session.commit()
    flash("%d preço(s) atualizado(s)!" % count, "success")
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
