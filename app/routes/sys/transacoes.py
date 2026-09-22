"""Origem do "Gerar" de contas a receber/pagar (previsão).

Quando o form de Conta a Receber/Pagar é aberto pelo "Gerar" (pedido/compra
com carteira de previsão), pré-preenche data/tipo/histórico e transfere o
`prazo_recebimento` da carteira para `transacao.prazo`. As previsões são
geradas no cliente pelo botão "Gerar" (JS) e persistidas junto com a conta.

Valor/conta_id são importados por `carry` (prop de campo, resolvida pelo
motor). A origem (`origem_pedido`/`origem_compra`) permanece na query string
— a `<form>` principal não tem `action` e reenvia os args no POST, usados por
`post_save_transacao`.
"""
from datetime import date

from flask import request, url_for

from ajsystem.core.extensions import db
from app.models.transacao import Transacao

_GERAR_JS = 'js/gerar_previsoes.js'


def _valor(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _carry_int(carry, key):
    try:
        return int(carry.get(key))
    except (TypeError, ValueError):
        return None


def _prazo_carteira(carteira_id):
    """`(prazo_texto, carteira_id)` da carteira (None se ausente/inválida)."""
    if not carteira_id:
        return None, None
    from app.models.carteira import Carteira
    cart = Carteira.query.get(carteira_id)
    if cart is None:
        return None, None
    return cart.prazo_recebimento, cart.id


def pre_get_transacao(mod, id):
    """`pre_get` de receber/pagar: pré-preenche mestre + prazo da carteira.

    Valor/conta são preenchidos pelo motor via `carry` (campos `valor`/
    `conta_id` na Schema). Aqui ficam data/tipo/histórico e o `prazo`
    transferido de `carteira.prazo_recebimento`. Nada é persistido e nenhuma
    previsão é criada — o botão "Gerar" (JS) cuida disso no form.

    O JS do "Gerar" é injetado via `_editor_js` (hook do layout) em todo form
    de receber/pagar (novo ou edição), inclusive manual.
    """
    extra = {'_editor_js': [url_for('static', filename=_GERAR_JS) + '?v=1']}
    if id is not None:
        return extra
    if not (request.args.get('origem_pedido') or request.args.get('origem_compra')):
        return extra

    pid = request.args.get('origem_pedido', type=int)
    if pid:
        from app.models.pedido import Pedido
        from ajsystem.core.memory import carry_get
        pedido = Pedido.query.get(pid)
        if pedido is None or pedido.transacao or pedido.movto:
            return extra
        carry = carry_get(request.args.get('carry')) or {}
        cart_id_carry = _carry_int(carry, 'carteira_id')
        prazo, _ = _prazo_carteira(cart_id_carry or pedido.carteira_id)
        extra['instance'] = Transacao(
            data=date.today(),
            tipo="R",
            prazo=prazo or '',
            historico=pedido.observacao or f"Venda Pedido #{pedido.id}",
        )
        return extra

    cid = request.args.get('origem_compra', type=int)
    if cid:
        from app.models.compra import Compra
        from ajsystem.core.memory import carry_get
        compra = Compra.query.get(cid)
        if compra is None or compra.transacao or compra.movto:
            return extra
        carry = carry_get(request.args.get('carry')) or {}
        cart_id_carry = _carry_int(carry, 'carteira_id')
        prazo, _ = _prazo_carteira(cart_id_carry or compra.carteira_id)
        extra['instance'] = Transacao(
            data=date.today(),
            tipo="P",
            prazo=prazo or '',
            historico=compra.observacao or f"Compra #{compra.id}",
        )
        return extra

    return extra


def post_save_transacao(instance, changed, old_vals):
    """`post_save` de receber/pagar: vincula a transação ao pedido/compra.

    Recalcula os agregados derivados das previsões (variacao, saldo e status).
    `valor` e `prazo` são alvo/entrada do usuário (vêm do form ou do `carry`)
    e não são sobrescritos aqui.
    """
    from ajsystem.core.memory import carry_take
    carry = carry_take(request.args.get('carry')) or {}
    previsoes = instance.previsoes or []
    instance.variacao = sum(_valor(v.variacao) for v in previsoes)
    instance.saldo = sum(_valor(v.previsto) + _valor(v.variacao)
                         - _valor(v.realizado) for v in previsoes)
    instance.status = instance.calc_status()
    pid = request.args.get('origem_pedido', type=int)
    if pid:
        from app.models.pedido import Pedido
        p = Pedido.query.get(pid)
        if p and not p.transacao and not p.movto:
            instance.pedido_id = p.id
            p.faturado_em = date.today()
            if not p.carteira_id and carry.get('carteira_id'):
                p.carteira_id = int(carry['carteira_id'])
                p.status = p.calc_status()
            db.session.commit()
            p.status = p.calc_status()
            db.session.commit()
        return
    cid = request.args.get('origem_compra', type=int)
    if cid:
        from app.models.compra import Compra
        c = Compra.query.get(cid)
        if c and not c.transacao and not c.movto:
            instance.compra_id = c.id
            c.faturado_em = date.today()
            if not c.carteira_id and carry.get('carteira_id'):
                c.carteira_id = int(carry['carteira_id'])
                c.status = c.calc_status()
            db.session.commit()
            c.status = c.calc_status()
            db.session.commit()
        return
    db.session.commit()