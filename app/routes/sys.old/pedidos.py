from datetime import date, datetime
from flask import request, redirect, url_for, flash, render_template
from app.ajsystem.core.extensions import db
from app.ajsystem.core import auto
from app.ajsystem.core.do_report import print_report, do_report
from app.ajsystem.core.form import pesquise
from app.models.order import Order
from app.models.quote import Quote
from app.models.transacao import Transacao
from app.models.previsao import Previsao
from app.models.movto import Movto
from app.models.recurso import Recurso
from app.models.producao import Producao  # noqa: needed for Order mapper resolution
from app.models.operacao import Operacao  # noqa: needed for Transacao mapper resolution
from app.constantes import ORDER_STATUS, FORMINHAS
from app.reports import PEDIDO_REPORT
from app.utils import parse_prazo_recebimento, _save_event

tipos_evento_list = [
    "Aniversário", "Casamento", "Debutante", "Corporativo",
    "Infantil", "Família", "Confraternização", "Religioso", "Outros",
]
tipos_evento = {t: t for t in tipos_evento_list}


def _preco_on_set(row):
    if row.get('preco_unitario'):
        return
    try:
        pid = int(row.get('product_id'))
    except (TypeError, ValueError):
        return
    valor = pesquise('product', pid, 'preco')
    if valor is None:
        return
    row['preco_unitario'] = float(valor)


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

    _save_event(instance, request.form)

    if not instance.quote_id:
        quote = Quote.query.filter_by(pedido_id=instance.id).first()
        if quote:
            instance.quote_id = quote.id


def _btn_print_action(instance):
    if instance is None or not instance.items:
        return ''
    return print_report(PEDIDO_REPORT, instance)


def _btn_gerar_action(instance):
    return url_for('pedidos.gerar_financeiro', id=instance.id)


def _btn_orcamento_action(instance):
    return url_for('orcamentos.form', id=instance.quote_id)


def _btn_cancelar_action(instance):
    return url_for('pedidos.cancelar', id=instance.id)


Entity = {
    'Order': {
        'id':                    {'type': 'ID', 'mask': '999.999', 'readonly': True},
        'client_id':             {'type': 'FK', 'label': 'Cliente', 'width': 20,
                                  'query': {'model': 'conta', 'when': 'ativo = true AND tipo IN (0, 1)'},
                                  'required': True},
        'data_pedido':           {'type': 'DATA_HORA', 'label': 'Data', 'width': 10},
        'data_previsao_entrega': {'type': 'DATA_HORA', 'label': 'Prev. Entrega', 'width': 10},
        'data_entrega':          {'type': 'DATA_HORA', 'label': 'Data Entrega', 'width': 10},
        'carteira_id':           {'type': 'FK', 'label': 'Pagamento', 'width': 15,
                                  'query': {'model': 'carteira', 'when': 'uso IN (0, 1)'}},
        'forminhas':             {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
        'total':                 {'type': 'NUM', 'currency': 'brl', 'readonly': True, 'width': 10},
        'status':                {'type': 'LIST', 'readonly': True, 'width': 10, 'options': ORDER_STATUS},
        'transacao_id':          {'type': 'FK', 'label': 'Faturado', 'width': 10,
                                  'masterkey': 'transacao', 'in_filter': 0, 'in_form': 0},
        'quote_id':              {'type': 'FK', 'label': 'Orçamento', 'width': 9, 'in_filter': 0,
                                  'in_form': 0},
        'movto_id':              {'type': 'FK', 'label': 'Recebimento', 'width': 10,
                                  'masterkey': 'movto', 'in_filter': 0, 'in_form': 0},
        'observacao':            {'type': 'MEMO', 'label': 'Observação', 'in_list': 0},
    },
'OrderItem': {
        'product_id':       {'type': 'FK', 'label': 'Produto', 'required': True,
                             'on_set': _preco_on_set},
        'quantidade':       {'type': 'INT', 'label': 'Qtd'},
        'preco_unitario':   {'type': 'NUM', 'label': 'Preço', 'step': '0.01'},
        'valor':            {'type': 'NUM', 'label': 'Valor', 'currency': 'brl', 'calc': 'quantidade * preco_unitario', 'in_form': 0},
        'observacao':       {'type': 'TEXT', 'label': 'Obs'},
    },
    'Event': {
        'id':         {'type': 'ID'},
        'order_id':   {'type': 'ID', 'in_form': 0},
        'tipo':       {'type': 'LIST', 'label': 'Tipo', 'options': tipos_evento},
        'tema':       {'type': 'TEXT', 'label': 'Tema'},
        'convidados': {'type': 'INT', 'label': 'Nº Convidados'},
        'obs':        {'type': 'MEMO', 'label': 'Observação'},
        'data':       {'type': 'DATA', 'label': 'Data'},
        'hora':       {'type': 'HORA', 'label': 'Hora'},
        'local':      {'type': 'TEXT', 'label': 'Local'},
        'cerimonial': {'type': 'TEXT', 'label': 'Cerimonial'},
    },
    'Transacao': {
        'id':             {'type': 'ID'},
        'data':           {'type': 'DATA', 'label': 'Data'},
        'tipo':           {'type': 'TEXT', 'label': 'Tipo', 'in_form': 0},
        'conta_id':       {'type': 'FK', 'label': 'Conta',
                           'query': {'model': 'conta'}, 'in_form': 0},
        'fatura':         {'type': 'TEXT', 'label': 'Fatura'},
        'valor':          {'type': 'NUM', 'label': 'Valor', 'currency': 'brl'},
        'historico':      {'type': 'TEXT', 'label': 'Histórico'},
        'cancelado':      {'type': 'DATA', 'label': 'Cancelado'},
        'total_previsto': {'type': 'NUM', 'label': 'Previsto', 'currency': 'brl', 'in_form': 0},
    },
    'Previsao': {
        'transacao_id': {'type': 'FK', 'label': 'Transação',
                         'query': {'model': 'transacao'}},
        'id':           {'type': 'ID', 'label': 'Previsão'},
        'documento':    {'type': 'TEXT', 'transform': 'upper'},
        'vencimento':   {'type': 'DATA', 'label': 'Vencimento'},
        'previsto':     {'type': 'NUM', 'currency': 'brl'},
        'realizado':    {'type': 'NUM', 'currency': 'brl'},
        'variacao':     {'type': 'NUM', 'label': 'Variação', 'currency': 'brl'},
        'saldo':        {'type': 'NUM', 'currency': 'brl'},
    },
    'Movto': {
        'id':        {'type': 'ID', 'label': 'Recebimento'},
        'recurso':   {'type': 'FK', 'query': {'model': 'recurso'}},
        'valor':     {'type': 'NUM', 'currency': 'brl'},
        'historico': {'type': 'TEXT', 'label': 'Histórico', 'transform': 'title'},
    },
}

gerar_btn = {'label': 'Gerar Financeiro', 'icon': 'bi-cash-coin', 'color': 'success',
             'outline': False, 'action': _btn_gerar_action,
             'position': 'nav_right',
             'when': lambda i: i.transacao_id is None and i.movto_id is None}

Page = {
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'fields': 'Order',
            'ordering': ['data_entrega'],
        },
        'form': {
            'fields': 'Order',
            'pre_save': _orders_pre_save,
            'readonly_when': {'status': [9]},
            'flash_ok': 'Pedido criado!',
            'flash_update': 'Pedido atualizado!',
            'new_label': 'Pedido',
            'new_title': 'Incluir Pedido',
            'sessions': {
                'Itens do Pedido': {
                    'table': {
                        'columns': ['product_id', 'quantidade', 'preco_unitario', 'valor', 'observacao'],
                        'total': ['quantidade', 'valor'],
                    },
                },
                'Evento': {
                    'table': ['Event'],
                    'single': True,
                },
                '*Financeiro': {
                    'buttons': [gerar_btn],
                },
                'A RECEBER': {
                    'table': ['Previsao'],
                    'label': 'A Receber',
                    'attr': 'transacao.previsoes',
                    'readonly': True,
                    'when': lambda i: i is not None and i.transacao is not None,
                },
                'RECEBIMENTO': {
                    'table': ['Movto'],
                    'label': 'Recebimento',
                    'attr': 'movto',
                    'single': True,
                    'readonly': True,
                    'when': lambda i: i is not None and i.movto is not None,
                },
            },
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success',
                 'action': _btn_print_action, 'render': '#page-content',
                 'position': 'nav_right'},
                gerar_btn,
                {'label': 'Orçamento', 'icon': 'eye', 'color': 'info',
                 'action': _btn_orcamento_action, 'position': 'footer_left',
                 'when': lambda i: i.quote_id is not None},
                {'label': 'Cancelar Pedido', 'icon': 'xmark', 'color': 'danger',
                 'action': _btn_cancelar_action, 'method': 'POST',
                 'confirm_msg': 'Cancelar este pedido?', 'position': 'footer_left',
                 'when': lambda i: i.status != 9},
            ],
        },
    },
}


@auto.rota('/dashboard', endpoint='dashboard')
def dashboard():
    return redirect(url_for('pedidos.list'))


@auto.rota('/<int:id>/cancelar', methods=['POST'], endpoint='cancelar')
def cancelar(id):
    order = Order.query.get_or_404(id)
    if order.status == 9:
        flash("Pedido entregue não pode ser cancelado.", "warning")
        return redirect(url_for('pedidos.form', id=id))
    order.status = 3
    if order.transacao:
        order.transacao.cancelado = date.today()
    db.session.commit()
    flash("Pedido cancelado!", "success")
    return redirect(url_for('pedidos.form', id=id))


@auto.rota('/<int:id>/print', endpoint='print_order')
def print_order(id):
    order = Order.query.get_or_404(id)
    return print_report(PEDIDO_REPORT, order)


@auto.rota('/<int:id>/pdf', endpoint='pdf_order')
def pdf_order(id):
    order = Order.query.get_or_404(id)
    return do_report(PEDIDO_REPORT, order.items, instance=order,
                     filename=f"pedido_{order.id}.pdf")


@auto.rota('/<int:id>/gerar-financeiro', methods=['GET', 'POST'], endpoint='gerar_financeiro')
def gerar_financeiro(id):
    order = Order.query.get_or_404(id)
    if order.transacao_id or order.movto_id:
        flash("Financeiro já gerado para este pedido.", "warning")
        return redirect(url_for('pedidos.form', id=id))

    fp = order.carteira
    if not fp:
        flash("Selecione uma forma de pagamento antes de gerar o financeiro.", "warning")
        return redirect(url_for('pedidos.form', id=id))

    total = float(order.total or 0)
    taxa = float(fp.taxa_recebimento or 0)
    valor_liquido = round(total * (1 - taxa / 100), 2)

    if request.method == "POST":
        if fp.gerar == 0:
            recurso_id = request.form.get("recurso_id", type=int)
            if not recurso_id:
                flash("Selecione um recurso.", "warning")
                return redirect(url_for('pedidos.gerar_financeiro', id=id))
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
        return redirect(url_for('pedidos.form', id=id))

    recursos = Recurso.query.order_by(Recurso.nome).all()
    parcelas = []
    if fp.gerar == 1:
        parcelas = parse_prazo_recebimento(
            fp.prazo_recebimento,
            order.data_pedido.date(),
            order.data_entrega.date() if order.data_entrega else None,
            total,
        )

    return render_template("pages/construcao.html")
