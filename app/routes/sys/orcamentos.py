from flask import request, redirect, url_for, flash, render_template
from datetime import datetime, timezone
from ajsystem.core.extensions import db
from ajsystem.defs.constants import POS_0_NOT_EMPTY
from app.models.conta import Conta
from app.models.pedido import Pedido
from app.models.pedido_item import PedidoItem
from app.models.orcamento import Orcamento
from app.models.orcamento_item import OrcamentoItem
from app.botoes import BTN_ORC_APROVAR, BTN_ORC_ENV, BTN_ORC_RENOVAR


Schema = {
    'Orcamento': {
        'status': {'pos_form': 3, 'pos_filter':3,
                    'tag': {'colors': {0: 'warning', 1: 'info', 6: 'success'}}},
        'total': {'calc': {'type': 'agg', 'source': 'sum(OrcamentoItem.valor)'},
                  'pos_form': 0},
        'validade': {'pos_list':0}, 
        'validade_data': {'pos_form': 2},
        'carteira_id': { 'lookup': {'display': 'nome'}, 'pos_form': 0},
        'observacao': {'pos_list': 2},
        'pedido_id': {'pos_form': POS_0_NOT_EMPTY,
                'tag': {'link': 'pedidos.form', 'color': 'info'}},
    },
    'OrcamentoItem': {
        'produto_id': {
            'on_set': {'replaces': {
                'qtd': 'qtd_minima',
                'preco': 'preco',
            }},
        },
        'valor': {'pos_form': 0},
    },
    'Evento': {
        'obs': {'pos_list': 2},
    },
}

Page = {
    'label': 'Orçamento',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Orcamento',
            'order': ['id'],
        },
        'form': {
            'max_width':115,
            'fields': 'Orcamento',
            'readonly': lambda q: q is not None and q.pedido_id is not None,
            'delete': {
                'when': lambda q: q.pedido_id is None,
                'msg_ok': 'Orçamento excluído!',
                'msg_no': 'Exclua o pedido vinculado antes de excluir o orçamento.',
            },
            'buttons': [BTN_ORC_ENV, BTN_ORC_RENOVAR],
            'sessions': {
                'Itens do Orçamento': {
                    'buttons': [
                        {'label': 'Preços zerados', 'position': 'bottom_left',
                         'icon': 'currency-dollar', 'color': 'secondary',
                         'action': 'itUpdateZerados'},
                    ],
                    'table': {
                        'columns': ['OrcamentoItem'],
                        'totals': ['qtd', {'valor': 'total'}],
                    },
                },
                'Evento': {
                    'fields': ['Evento'],
                },
                'Financeiro': {
                    'buttons' : [BTN_ORC_APROVAR],
                    'fields':['total','carteira_id','pedido_id'],
                },
            },
        },
    },
}


def _converter_context(quote):
    """Clientes + sugestões para a página de aprovação (portado do antigo converter)."""
    clients = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([0, 1])).order_by(Conta.nome).all()
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


def _sem_total(quote):
    """True quando o orçamento não tem itens valorizados (total <= 0)."""
    return (quote.total or 0) <= 0


def aprovar(id):
    """Aprova o orçamento e gera o pedido a partir dele (antigo botão Converter).

    Rota registrada em `create_app` como `orcamentos.aprovar`
    (`/<int:id>/aprovar`, GET+POST), pois o motor gera apenas o CRUD.
    """
    quote = Orcamento.query.get_or_404(id)
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou rejeitado.", "warning")
        return redirect(url_for("orcamentos.list"))
    if _sem_total(quote):
        # Espelha o `enabled=['total']` do botão: um orçamento sem itens
        # valorizados viraria um pedido de valor zero.
        flash("Orçamento sem valor — adicione itens com quantidade e preço.", "warning")
        return redirect(url_for("orcamentos.form", id=id))

    if request.method == "GET":
        return render_template(
            "sys/converter.html",
            quote=quote,
            total=quote.total,
            clientes=_converter_context(quote),
        )

    tipo = request.form.get("converter_tipo", "existente")

    if tipo == "nova":
        nome = request.form.get("novo_nome", "").strip()
        telefone = request.form.get("novo_telefone", "").strip()
        if not nome:
            flash("Informe o nome da nova conta.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))
        existing = Conta.query.filter(Conta.nome.ilike(nome)).first()
        if existing:
            flash(f"Já existe uma conta com o nome '{existing.nome}'. Selecione-a na lista de contas existentes.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))
        conta = Conta(
            nome=nome,
            telefone=telefone or None,
            email=None,
            tipo=0,
        )
        db.session.add(conta)
        db.session.flush()
    else:
        conta_id = request.form.get("conta_id", type=int)
        conta = Conta.query.get(conta_id)
        if not conta:
            flash("Selecione um cliente para converter.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))

    order = Pedido(
        conta_id=conta.id,
        entregue_em=None,
        observacao=quote.observacao,
        carteira_id=quote.carteira_id,
        forminhas=quote.forminhas,
        status=0,
    )
    db.session.add(order)
    db.session.flush()

    for item in quote.items:
        order_item = PedidoItem(
            pedido_id=order.id,
            produto_id=item.produto_id,
            qtd=item.qtd,
            preco=item.preco,
            observacao=item.observacao,
        )
        db.session.add(order_item)

    db.session.flush()
    order.valor = sum(
        (i.preco or 0) * i.qtd for i in order.items
    )
    if quote.evento:
        order.evento = quote.evento
    quote.status = 9
    quote.pedido_id = order.id
    order.orcamento_id = quote.id

    db.session.commit()
    flash("Orçamento convertido para pedido!", "success")
    return redirect(url_for("orcamentos.list"))


def renovar(id):
    """Renova um orçamento expirado (status 7→6 + nova data de renovação).

    Rota registrada em `create_app` como `orcamentos.renovar`
    (`/<int:id>/renovar`, POST), pois o motor gera apenas o CRUD.
    """
    quote = Orcamento.query.get_or_404(id)
    if quote.status != 7:
        flash("Apenas orçamentos expirados podem ser renovados.", "warning")
        return redirect(url_for("orcamentos.list"))
    quote.data_renovacao = datetime.now(timezone.utc)
    quote.status = 6
    db.session.commit()
    flash("Orçamento renovado com sucesso!", "success")
    return redirect(url_for("orcamentos.form", id=id))
