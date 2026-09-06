"""Sincronismo movto <-> previsao (portado de old/ajsystem/sys/movimentos.py).

- criar: soma `variacao` e (se `sincronizar`) `valor` no `realizado` da previsão;
- editar: se o valor mudou (ou trocou a previsão), reverte na antiga e aplica
  na nova, zerando `variacao` e ligando `sincronizar` (igual ao antigo);
- excluir: reverte (via `excluir_movto`, usado pelas rotas custom).
"""
from decimal import Decimal

from flask import flash, redirect, url_for

from ajsystem.core.extensions import db
from app.models.previsao import Previsao


def _sync_previsao(previsao_id, valor, variacao, sincronizar, sinal):
    if not previsao_id:
        return False
    p = Previsao.query.get(previsao_id)
    if not p:
        return False
    if variacao:
        p.variacao = (p.variacao or 0) + Decimal(str(variacao)) * sinal
    if sincronizar:
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
        if _sync_previsao(new_pid, new_valor, instance.variacao,
                           instance.sincronizar, 1):
            db.session.commit()
        return
    if new_pid == old_pid and old_valor is not None and abs(new_valor - old_valor) < 0.01:
        return  # sem mudança relevante: sem sync (igual ao antigo)
    _sync_previsao(old_pid, old_valor or 0.0, old_vals.get('variacao'),
                   old_vals.get('sincronizar'), -1)
    instance.variacao = 0
    instance.sincronizar = True
    _sync_previsao(new_pid, new_valor, 0, True, 1)
    db.session.commit()


def excluir_movto(id, list_endpoint, label='Lançamento'):
    """Exclui movto revertendo a previsão + desvinculando compra/pedido."""
    from app.models.movimento import Movimento
    from app.models.compra import Compra
    from app.models.pedido import Pedido
    movto = Movimento.query.get(id)
    if not movto:
        flash("Registro inexistente", "warning")
        return redirect(url_for(list_endpoint))
    compra = Compra.query.filter_by(movimento_id=movto.id).first()
    order = Pedido.query.filter_by(movimento_id=movto.id).first()
    if compra:
        compra.movimento_id = None
    if order:
        order.movimento_id = None
    _sync_previsao(movto.previsao_id, float(movto.valor or 0),
                   movto.variacao, movto.sincronizar, -1)
    db.session.delete(movto)
    db.session.commit()
    flash(f"{label} excluído!", "success")
    if compra:
        return redirect(url_for("compras.form", id=compra.id))
    if order:
        return redirect(url_for("pedidos.form", id=order.id))
    return redirect(url_for(list_endpoint))
