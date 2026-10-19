from flask import flash, redirect, url_for

from ajsystem.core.formats import parse_brl
from ajsystem import locales as i18n
from app.models.pedido import Pedido
from app.extends.buttons import _sem_financeiro
from app.models.pedido_item import PedidoItem
from app.models.carteira import Carteira
from app.reports.pedidos import PEDIDO

Buttons = {
    'enviar_pedido': {'type': 'print', 'report': PEDIDO, 'label': i18n.SEND,
                      'icon': 'paper-airplane', 'color': 'success',
                      'position': 'top_right'},
}


def _num(v):
    """Numérico tolerante a 'R$ 1.234,56' (o input calc manda formatado)."""
    n = parse_brl(v)
    return 0.0 if n is None else n


def _child_soma(request, rel='items'):
    from re import match as _match
    rows = {}
    for key, val in request.form.items():
        m = _match(r'^child_%s_(.+?)_(qtd|preco)$' % rel, key)
        if not m:
            continue
        rows.setdefault(m.group(1), {})[m.group(2)] = _num(val)
    return sum((r.get('qtd') or 0) * (r.get('preco') or 0) for r in rows.values())


def _soma_itens(instance):
    return sum(_num(i.valor) for i in (instance.items or []))


def _pre_save(instance, request, is_new):
    acrescimo = _num(request.form.get('acrescimo'))
    desconto = _num(request.form.get('desconto'))
    if acrescimo < 0 or desconto < 0:
        flash('Acréscimo e desconto não podem ser negativos.', 'warning')
        return False
    if _child_soma(request) + acrescimo - desconto < 0:
        flash('Total negativo: desconto não pode exceder o valor dos itens somado ao acréscimo.', 'warning')
        return False
    instance.status = instance.calc_status()


def _post_save(instance, changed, old_vals):
    from ajsystem.core.extensions import db
    instance.valor = _soma_itens(instance)
    instance.status = instance.calc_status()
    db.session.commit()


def _faturado(instance):
    return (instance is not None and instance.faturado_em is not None
            and bool(instance.transacao or instance.movto))


def _pre_get(mod, id):
    from flask import request
    if id is None or request.method != 'GET':
        return None
    pedido = Pedido.query.get(id)
    if pedido is None or not pedido.faturado_em:
        return None
    if not (pedido.transacao or pedido.movto):
        pedido.faturado_em = None
        pedido.status = pedido.calc_status()
        try:
            from ajsystem.core.extensions import db
            db.session.commit()
        except Exception:
            db.session.rollback()
        flash("Faturamento revertido: lançamento em contrapartida não existe.", "warning")
    return None


def gerar_financeiro(id):
    from flask import request
    from ajsystem.core.memory import store_carry

    pedido = Pedido.query.get_or_404(id)
    if pedido.transacao or pedido.movto:
        flash("Financeiro já gerado para este pedido.", "warning")
        return redirect(url_for("pedidos.form", id=id))

    cart_id = request.form.get('carteira_id', type=int) or pedido.carteira_id
    cart = Carteira.query.get(cart_id) if cart_id else None
    if not cart:
        flash("Selecione uma forma de pagamento antes de gerar o financeiro.", "warning")
        return redirect(url_for("pedidos.form", id=id))

    carry_token = store_carry(request.form)

    if cart.gerar == 1:
        return redirect(url_for("receber.form", origem_pedido=pedido.id, carry=carry_token))

    total = _num(request.form.get('total') or pedido.total)
    return redirect(url_for(
        "recebimentos.form",
        origem_pedido=pedido.id,
        valor=total,
        conta_id=request.form.get('conta_id', type=int) or pedido.conta_id,
        carry=carry_token,
    ))


def _financeiro_gerado(instance):
    return instance is not None and bool(instance.transacao or instance.movto)


def _query_financeiro(instance):
    if instance is None or not (instance.transacao or instance.movto):
        return None
    if instance.transacao:
        return {'columns': ['Previsao'], 'attr': 'transacao.previsoes'}
    return {'columns': ['Movimento'], 'attr': 'movto'}


Schema = {
    'Pedido': {
        'conta_id': {'label': 'Cliente',
                      'lookup': {'display': 'nome', 'fields': ['nome', 'telefone'],
                                 'when': {'ativo': True, 'tipo': [0, 1]}}},
        'carteira_id': {'label': 'Pagamento',
                        'lookup': {'display': 'nome'},
                        'disabled': _financeiro_gerado},
        'pedido_em': {},
        'faturado_em': {},
        'cancelado_em': {},
        'entregue_em': {},
        'valor': {'calc': {'type': 'agg', 'source': 'sum(PedidoItem.valor)',
                           'diff': 'Aviso de Inconsistência: Valor registrado neste pedido difere da soma dos itens atuais.'}},
        'acrescimo': {},
        'desconto': {},
        'total': {'calc': 'valor + acrescimo - desconto'},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado deste pedido difere do status calculado.'},
                   'tag': {'colors': {0: 'warning', 1: 'success', 2: 'info', 3: 'info', 8: 'error', 9: 'success'}}},
        'transacao_id': {'tag': {'link': 'receber.form', 'color': 'info'}},
        'movto_id': {'tag': {'link': 'recebimentos.form', 'color': 'info'}},
    },
    'PedidoItem': {
        'produto_id': {
            'on_set': {'replaces': {
                'qtd': 'qtd_minima',
                'preco': 'preco',
            }},
        },
        'valor': {},
    },
    'Previsao': {
        'id': {'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
    },
}

Page = {
    'label': 'Pedido',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Pedido',
            'filter': {'types': {'checklist': 'status'}},
            'hidden': ['transacao_id', 'movto_id', 'observacao'],
            'card': ['pedido_em', 'faturado_em', 'cancelado_em',
                     'entregue_em'],
            'order': ['entregue_em'],
        },
        'form': {
            'max_width': 130,
            'fields': 'Pedido',
            'positions': {
                'bar':    ['status'],
                'footer': ['cancelado_em'],
                'hidden': ['transacao_id', 'movto_id', 'carteira_id', 'valor',
                           'acrescimo', 'desconto', 'total', 'pedido_em',
                           'faturado_em', 'entregue_em'],
            },
            'visible': {'transacao_id': {'not_empty': True},
                        'movto_id': {'not_empty': True}},
            'readonly': _faturado,
            'pre_get': _pre_get,
            'pre_save': _pre_save,
            'post_save': _post_save,
            'flash_ok': 'Pedido criado!',
            'flash_update': 'Pedido atualizado!',
            'buttons': ['enviar_pedido'],
            'sessions': {
                'Itens do Pedido': {
                    'table': {
                        'columns': ['PedidoItem'],
                        'totals': ['qtd', {'valor': 'valor'}],
                    },
                    'positions': {'hidden': ['valor']},
                },
                'Evento': {
                    'fields': ['Evento'],
                },
                'Financeiro': {
                    'fields': ['valor', 'acrescimo', 'desconto', 'total',
                               'carteira_id', 'transacao_id', 'movto_id'],
                    'query': _query_financeiro,
                    'buttons': [
                        {'gerar_financeiro': {
                            'url': 'pedidos.gerar_financeiro', 'method': 'POST', 'position': 'after',
                            'confirm_msg': 'Gerar o financeiro deste pedido?',
                            'visible': _sem_financeiro,
                            'enabled': ['total', 'carteira_id'],
                            'carry': {'map': {'valor': 'total'}}}},
                    ],
                },
            },
        },
    },
}
