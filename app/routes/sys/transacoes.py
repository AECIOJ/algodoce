"""Origem do "Gerar" de contas a receber/pagar (previsão).

Quando o form de Conta a Receber/Pagar é aberto pelo "Gerar" (pedido/compra
com carteira de previsão), pré-preenche data/tipo/histórico e, quando a
carteira tem `prazo_recebimento`, gera as previsões iniciais (vencimentos).
Valor/conta_id são importados por `carry` (prop de campo, resolvida pelo
motor). A origem (`origem_pedido`/`origem_compra`) permanece na query string
— a `<form>` principal não tem `action` e reenvia os args no POST, usados por
`post_save_transacao`.
"""
from datetime import date

from flask import request

from ajsystem.core.extensions import db
from app.models.transacao import Transacao


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


def _gerar_previsoes(prazo_texto, total, carteira_id):
    """Gera `Previsao` em memória a partir do prazo da carteira ([ ] se vazio)."""
    from app.utils import parse_prazo_recebimento
    from app.models.previsao import Previsao
    if not prazo_texto or not prazo_texto.strip():
        return []
    vencimentos = parse_prazo_recebimento(prazo_texto, date.today(), total=total)
    return [Previsao(vencimento=v['vencimento'], previsto=v['previsto'],
                     carteira_id=carteira_id)
            for v in vencimentos]


def pre_get_transacao(mod, id):
    """`pre_get` de receber/pagar: pré-preenche mestre + previsões da carteira.

    Valor/conta são preenchidos pelo motor via `carry` (campos `valor`/
    `conta_id` na Schema). Aqui ficam data/tipo/histórico e a geração das
    previsões quando a carteira tem `prazo_recebimento`. Nada é persistido.
    """
    if id is not None:
        return None
    if not (request.args.get('origem_pedido') or request.args.get('origem_compra')):
        return None

    pid = request.args.get('origem_pedido', type=int)
    if pid:
        from app.models.pedido import Pedido
        from ajsystem.core.memory import carry_get
        pedido = Pedido.query.get(pid)
        if pedido is None or pedido.transacao or pedido.movto:
            return None
        carry = carry_get(request.args.get('carry')) or {}
        total = _valor(carry.get('valor') or pedido.total)
        cart_id_carry = _carry_int(carry, 'carteira_id')
        prazo, cart_id = _prazo_carteira(cart_id_carry or pedido.carteira_id)
        inst = Transacao(
            data=date.today(),
            tipo="R",
            historico=pedido.observacao or f"Venda Pedido #{pedido.id}",
        )
        if prazo:
            inst.previsoes = _gerar_previsoes(prazo, total, cart_id)
        return {'instance': inst}

    cid = request.args.get('origem_compra', type=int)
    if cid:
        from app.models.compra import Compra
        from ajsystem.core.memory import carry_get
        compra = Compra.query.get(cid)
        if compra is None or compra.transacao or compra.movto:
            return None
        carry = carry_get(request.args.get('carry')) or {}
        total = _valor(carry.get('valor') or compra.total)
        cart_id_carry = _carry_int(carry, 'carteira_id')
        prazo, cart_id = _prazo_carteira(cart_id_carry or compra.carteira_id)
        inst = Transacao(
            data=date.today(),
            tipo="P",
            historico=compra.observacao or f"Compra #{compra.id}",
        )
        if prazo:
            inst.previsoes = _gerar_previsoes(prazo, total, cart_id)
        return {'instance': inst}

    return None


def post_save_transacao(instance, changed, old_vals):
    """`post_save` de receber/pagar: vincula a transação ao pedido/compra.

    Persiste os agregados físicos calculados a partir das previsões
    (valor = Σ previsto, prazo = resumo dos vencimentos, variacao e saldo
    como no list), além do status — mesmo no fluxo manual (sem origem).
    """
    from ajsystem.core.memory import carry_take
    carry = carry_take(request.args.get('carry')) or {}
    previsoes = instance.previsoes or []
    instance.valor = sum(_valor(v.previsto) for v in previsoes)
    instance.prazo = instance.calc_prazo()
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