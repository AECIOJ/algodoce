"""Sincronismo movto <-> previsao (portado de old/ajsystem/sys/movimentos.py).

- criar: soma `variacao` e `valor` no `realizado` da previsão;
- editar: se o valor mudou (ou trocou a previsão), reverte na antiga e aplica
  na nova, zerando `variacao` (igual ao antigo);
- excluir: reverte (via `excluir_movto`, usado pelas rotas custom).
"""
from decimal import Decimal

from flask import flash, redirect, url_for

from ajsystem.core.extensions import db
from ajsystem.defs.constants import TODAY
from app.models.previsao import Previsao


def _desvincular_origem(instance, message=True):
    """Previsão vence: desvincula pedido/compra do movimento e reverte o
    faturamento vinculado (igual ao excluir_movto), liberando o salvamento."""
    from app.models.pedido import Pedido
    from app.models.compra import Compra
    revertido = []
    if instance.pedido_id:
        pedido = Pedido.query.get(instance.pedido_id)
        instance.pedido_id = None
        if pedido:
            pedido.faturado_em = None
            pedido.status = pedido.calc_status()
            revertido.append(f'Pedido {pedido.id}')
    if instance.compra_id:
        compra = Compra.query.get(instance.compra_id)
        instance.compra_id = None
        if compra:
            compra.faturado_em = None
            compra.status = compra.calc_status()
            revertido.append(f'Compra {compra.id}')
    if message:
        if revertido:
            flash('Previsão selecionada: vínculo com ' + ', '.join(revertido)
                  + ' desfeito e faturamento revertido.', 'warning')
        else:
            flash('Previsão selecionada: vínculo com pedido/compra ignorado.',
                  'warning')


def _validar_origem_exclusiva(instance, request=None, is_new=None):
    """"pre_save" de pagamentos/recebimentos: previsão e pedido/compra são
    mutuamente exclusivos. Como a previsão prevalece, quando ambas estão no
    POST (ou há origem na query string) desvincula pedido/compra, reverte o
    faturamento e libera o salvamento em vez de bloquear."""
    if not instance.previsao_id:
        return True
    origem_fluxo = False
    if request is not None:
        origem_fluxo = bool(request.args.get('origem_pedido')
                            or request.args.get('origem_compra'))
    if not (instance.pedido_id or instance.compra_id or origem_fluxo):
        return True
    _desvincular_origem(instance)
    return True


def _pre_get_movto(mod, id):
    """`pre_get` de recebimentos/pagamentos.

    Quando o form é aberto pelo "Gerar" via Movimento (a vista), pré-preenche
    o lançamento com a data do pedido/compra. `valor`/`conta_id` são
    importados pelo motor via `carry` (prop nos campos da Schema; a origem
    permanece na query string junto com o token). `previsao_id` e o vínculo
    concorrente ficam ocultos — a origem do fluxo é pedido/compra
    (mutuamente exclusivo com previsão).
    """
    from flask import request
    if id is not None:
        return None
    if not (request.args.get('origem_pedido') or request.args.get('origem_compra')):
        return None
    from app.models.movimento import Movimento

    if request.args.get('origem_pedido'):
        from app.models.pedido import Pedido
        pedido = Pedido.query.get(request.args.get('origem_pedido', type=int))
        if pedido is None or pedido.transacao or pedido.movto:
            return None
        return {'instance': Movimento(data=pedido.pedido_em),
                'hidden': ['previsao_id', 'compra_id']}
    from app.models.compra import Compra
    compra = Compra.query.get(request.args.get('origem_compra', type=int))
    if compra is None or compra.transacao or compra.movto:
        return None
    return {'instance': Movimento(data=compra.data),
            'hidden': ['previsao_id', 'pedido_id']}


def _link_movto_origem(instance):
    from flask import request
    from ajsystem.core.memory import carry_take
    if instance.previsao_id:
        return
    carry = carry_take(request.args.get('carry')) or {}
    pid = request.args.get('origem_pedido', type=int)
    if pid:
        from app.models.pedido import Pedido
        p = Pedido.query.get(pid)
        if p and not p.transacao and not p.movto:
            instance.pedido_id = p.id
            p.faturado_em = TODAY()
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
            c.faturado_em = TODAY()
            if not c.carteira_id and carry.get('carteira_id'):
                c.carteira_id = int(carry['carteira_id'])
                c.status = c.calc_status()
            db.session.commit()
            c.status = c.calc_status()
            db.session.commit()


def post_save_movto_link(instance, changed, old_vals):
    """`post_save` de recebimentos/pagamentos: sync previsão + vínculo origem."""
    sync_movto_save(instance, changed, old_vals)
    _link_movto_origem(instance)


def _sync_previsao(previsao_id, valor, variacao, sinal):
    if not previsao_id:
        return False
    p = Previsao.query.get(previsao_id)
    if not p:
        return False
    if variacao:
        p.variacao = (p.variacao or 0) + Decimal(str(variacao)) * sinal
    p.realizado = max(0, (p.realizado or 0) + Decimal(str(valor)) * sinal)
    return True


def _fnum(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def sync_movto_save(instance, changed, old_vals):
    """`post_save` de recebimentos/pagamentos (roda após o commit)."""
    old_vals = old_vals or {}
    new_pid = instance.previsao_id
    old_pid = old_vals.get('previsao_id')
    new_valor = _fnum(instance.valor) or 0.0
    old_valor = _fnum(old_vals.get('valor'))
    is_new = old_pid is None and old_valor is None
    if is_new:
        if _sync_previsao(new_pid, new_valor, instance.variacao, 1):
            db.session.commit()
        return
    if new_pid == old_pid and old_valor is not None and abs(new_valor - old_valor) < 0.01:
        return  # sem mudança relevante: sem sync (igual ao antigo)
    _sync_previsao(old_pid, old_valor or 0.0, old_vals.get('variacao'), -1)
    instance.variacao = 0
    _sync_previsao(new_pid, new_valor, 0, 1)
    db.session.commit()


def excluir_movto(id, list_endpoint, label='Lançamento'):
    """Exclui movto revertendo a previsão. O vínculo com pedido/compra cai
    junto; o faturamento vinculado também é revertido (rollback) — pedido e
    compra voltam a um estado editável (sem contrapartida não há faturamento)."""
    from app.models.movimento import Movimento
    movto = Movimento.query.get(id)
    if not movto:
        flash("Registro inexistente", "warning")
        return redirect(url_for(list_endpoint))
    compra = movto.compra
    order = movto.pedido
    _sync_previsao(movto.previsao_id, float(movto.valor or 0),
                   movto.variacao, -1)
    db.session.delete(movto)
    db.session.commit()
    if compra:
        compra.faturado_em = None
        compra.status = compra.calc_status()
        db.session.commit()
    if order:
        order.faturado_em = None
        order.status = order.calc_status()
        db.session.commit()
    flash(f"{label} excluído!", "success")
    if compra:
        return redirect(url_for("compras.form", id=compra.id))
    if order:
        return redirect(url_for("pedidos.form", id=order.id))
    return redirect(url_for(list_endpoint))
