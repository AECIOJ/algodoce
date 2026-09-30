from flask import flash, redirect, url_for

from ajsystem.core.formats import parse_brl
from ajsystem.defs.constants import POS_0_NOT_EMPTY
from ajsystem import locales as i18n
from app.models.pedido import Pedido
from app.botoes import _sem_financeiro
from app.models.pedido_item import PedidoItem
from app.models.carteira import Carteira
from app.reports.pedidos import PEDIDO


# `report` + `type: 'print'` declara o botão de relatório: `render`, `into` e o
# `guard` padrão (`_has_items`) saem sozinhos, e o que fica escrito é a
# aparência de envio (papagaio/verde) em vez do documento azul do `print`.
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
    """Soma `qtd * preco` das linhas child enviadas no POST (validação)."""
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
    """Self-heal: `faturado_em` órfão (sem contrapartida movto/transacao) é
    revertido no load do form — evita pedido travado como "faturado"."""
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
        'carteira_id': {'label': 'Pagamento', 'pos_form': 0,
                        'lookup': {'display': 'nome'},
                        'disabled': _financeiro_gerado},
        'pedido_em': {'pos_form': 0,'pos_list': 2},
        'faturado_em': {'pos_form': 0,'pos_list': 2},
        'cancelado_em': {'pos_form': 5,'pos_list': 2},
        'entregue_em': {'pos_form': 0,'pos_list': 2},
        'valor': {'calc': {'type': 'agg', 'source': 'sum(PedidoItem.valor)',
                           'diff': 'Aviso de Inconsistência: Valor registrado neste pedido difere da soma dos itens atuais.'},
                  'pos_form': 0},
        'acrescimo': {'pos_form': 0},
        'desconto': {'pos_form': 0},
        'total': {'calc': 'valor + acrescimo - desconto', 'pos_form': 0},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado deste pedido difere do status calculado.'},
                   'pos_form': 3, 'pos_filter': 3, 'tag': {'colors': {0: 'warning', 1: 'success', 2: 'info', 3: 'info', 8: 'error', 9: 'success'}}},
        'transacao_id': {'pos_form': POS_0_NOT_EMPTY, 'pos_list': 0,
                         'tag': {'link': 'receber.form', 'color': 'info'}},
        'movto_id': {'pos_form': POS_0_NOT_EMPTY, 'pos_list': 0,
                     'tag': {'link': 'recebimentos.form', 'color': 'info'}},
        'observacao': {'pos_list': 0},
    },
    'PedidoItem': {
        'produto_id': {
            'on_set': {'replaces': {
                'qtd': 'qtd_minima',
                'preco': 'preco',
            }},
        },
        'valor': {'pos_form': 0},
    },
    'Previsao': {
        'id': {'pos_form': 1, 'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
    },
    'Evento': {
        'obs': {'pos_list': 2},
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
            'order': ['entregue_em'],
        },
        'form': {
            'max_width': 130,
            'fields': 'Pedido',
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
                },
                'Evento': {
                    'fields': ['Evento'],
                },
                'Financeiro': {
                    'fields': ['valor', 'acrescimo', 'desconto', 'total',
                               'carteira_id', 'transacao_id', 'movto_id'],
                    'query': _query_financeiro,
                    'buttons': [
                        # Rótulo, ícone (cédula -> moeda), cor e estilo saem do
                        # tipo `gerar_financeiro` do app. Aqui ficam só o que é
                        # deste uso: destino, confirmação, visibilidade, campos
                        # que habilitam e o que é carregado para o formulário.
                        {'gerar_financeiro': {
                            'url': 'pedidos.gerar_financeiro', 'method': 'POST', 'position': 'right',
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