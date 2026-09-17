from datetime import date
from flask import flash, redirect, url_for
from ajsystem.core.do_report import print_report
from ajsystem.defs.constants import POS_EXPLICIT_NOT_EMPTY
from app.models.compra import Compra
from app.models.compra_item import CompraItem
from app.reports.compras import COMPRA


def _num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _child_soma(request, rel='items'):
    """Soma `qtd * preco` das linhas child enviadas no POST (validação)."""
    from re import match as _match
    rows = {}
    for key, val in request.form.items():
        m = _match(r'^child_%s_(.+?)_(qtd|preco)$' % rel, key)
        if not m:
            continue
        try:
            rows.setdefault(m.group(1), {})[m.group(2)] = float(val or 0)
        except (TypeError, ValueError):
            continue
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
    if instance.status in (6, 9) and not instance.observacao:
        return False


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
    revertido no load do form — evita compra travada como "faturada"."""
    from flask import request
    if id is None or request.method != 'GET':
        return None
    compra = Compra.query.get(id)
    if compra is None or not compra.faturado_em:
        return None
    if not (compra.transacao or compra.movto):
        compra.faturado_em = None
        compra.status = compra.calc_status()
        try:
            from ajsystem.core.extensions import db
            db.session.commit()
        except Exception:
            db.session.rollback()
        flash("Faturamento revertido: lançamento em contrapartida não existe.", "warning")
    return None


def _sem_financeiro(instance):
    return instance is not None and not instance.transacao and not instance.movto


def _financeiro_gerado(instance):
    return instance is not None and bool(instance.transacao or instance.movto)


def _query_financeiro(instance):
    if instance is None or not (instance.transacao or instance.movto):
        return None
    if instance.transacao:
        return {'columns': ['Previsao'], 'attr': 'transacao.previsoes'}
    return {'columns': ['Movimento'], 'attr': 'movto'}


def gerar_financeiro(id):
    from flask import request
    from ajsystem.core.memory import store_carry
    from app.models.carteira import Carteira

    compra = Compra.query.get_or_404(id)
    if compra.transacao or compra.movto:
        flash("Financeiro já gerado para esta compra.", "warning")
        return redirect(url_for("compras.form", id=id))

    cart_id = request.form.get('carteira_id', type=int) or compra.carteira_id
    cart = Carteira.query.get(cart_id) if cart_id else None
    if not cart:
        flash("Selecione uma forma de pagamento antes de gerar o financeiro.", "warning")
        return redirect(url_for("compras.form", id=id))

    carry_token = store_carry(request.form)

    if cart.gerar == 1:
        return redirect(url_for("pagar.form", origem_compra=compra.id, carry=carry_token))

    total = float(request.form.get('total') or compra.total or 0)
    return redirect(url_for(
        "pagamentos.form",
        origem_compra=compra.id,
        valor=total,
        conta_id=compra.fornecedor_id,
        carry=carry_token,
    ))


def _btn_enviar_action(instance):
    """Botão Enviar do form — pré-controle + impressão da compra.

    Exibição no padrão das listagens (operações/PLANO): o fragmento vai para
    o container exclusivo `#report-content` (via `render`).
    """
    if instance is None or not instance.items:
        return ''
    return print_report(COMPRA, instance)


Schema = {
    'Compra': {
        'data': {'default': date.today},
        'fornecedor_id': {'label': 'Fornecedor',
                           'lookup': {'display': 'nome', 'fields': ['nome', 'telefone'],
                                      'when': {'ativo': True, 'tipo': [1, 2]}}},
        'carteira_id': {'label': 'Pagamento', 'pos_form':0,
                        'lookup': {'display': 'nome'},
                        'disabled': _financeiro_gerado},
        'status': {'calc': {'type': 'call', 'source': 'calc_status',
                            'diff': 'Aviso de Inconsistência: Status registrado desta compra difere do status calculado.'},
                   'pos_form': 3, 'pos_filter': 3, 'tag': {'colors': {0: 'warning', 1: 'info', 2: 'info', 6: 'warning', 8: 'success', 9: 'error'}}},
        'transacao_id': {'pos_form': POS_EXPLICIT_NOT_EMPTY, 'pos_list': 0,
                         'tag': {'link': 'pagar.form', 'color': 'info'}},
        'movto_id': {'pos_form': POS_EXPLICIT_NOT_EMPTY, 'pos_list': 0,
                     'tag': {'link': 'pagamentos.form', 'color': 'info'}},
'valor': {'calc': {'type': 'agg', 'source': 'sum(CompraItem.valor)',
                            'diff': 'Aviso de Inconsistência: Total registrado desta compra difere da soma dos itens atuais.'},
                   'readonly': True, 'pos_form': 0},
        'acrescimo': {'pos_form': 0},
        'desconto': {'pos_form': 0},
        'total': {'calc': 'valor + acrescimo - desconto', 'pos_form': 0},
        'pedido_em': {'pos_form': 0},
        'faturado_em': {'pos_form': 0},
        'cancelado_em': {'pos_form': 5},
        'recebido_em': {'pos_form': 0},
        'devolvido_em': {'pos_form': 0},
    },
    'CompraItem': {
        'insumo_id': {
            'lookup': {'display': 'nome', 'fields': ['nome']},
        },
        'valor': {'pos_form': 0},
    },
    'Previsao': {
        'id': {'pos_form': 1, 'readonly': True, 'label': 'Previsão', 'mask': '999,999'},
    },
}

Page = {
    'label': 'Compra',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Compra',
            'order': ['data', 'id'],
        },
        'form': {
            'max_width':120,
            'fields': 'Compra',
            'readonly': _faturado,
            'pre_get': _pre_get,
            'pre_save': _pre_save,
            'post_save': _post_save,
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success', 'outline': True,
                 'action': _btn_enviar_action, 'render': '#report-content',
                 'position': 'nav_right'},
            ],
            'sessions': {
                'Itens': {
                    'table': {
                        'columns': ['CompraItem'],
                        'totals': ['qtd', {'valor': 'valor'}],
                    },
                },
                'Financeiro': {
                    'fields': ['valor', 'acrescimo', 'desconto', 'total',
                               'carteira_id', 'transacao_id', 'movto_id'],
                    'query': _query_financeiro,
                    'buttons': [
                        {'label': 'Gerar', 'icon': 'banknotes', 'color': 'success', 'outline': True,
                         'endpoint': 'compras.gerar_financeiro', 'url_var': 'id', 'method': 'POST', 'position': 'fields_right',
                         'confirm_msg': 'Gerar o financeiro desta compra?',
                         'when': _sem_financeiro,
                         'enable_when': ['valor', 'carteira_id'],
                         'carry': {'map': {'valor': 'valor', 'conta_id': 'fornecedor_id'}}},
                    ],
                },

            },
        },
    },
}
