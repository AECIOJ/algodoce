import sys

from flask import jsonify, redirect, request, session, url_for

from ajsystem.core import auto
from ajsystem.core.cart import (
    count_items,
    minimo_quantidade,
    resolve_cart,
    send_cart,
)
from ajsystem.core.ntfy import notificar as aj_notificar
from ajsystem.defs.cart import CART_SESSION_KEY, CLIENT_SESSION_KEY
from app.constantes import FORMINHAS, QUOTE_STATUS, tipos_evento
from app.models.configuracao import Configuracao

Entity = {
    'Orcamento': {
        'cliente_nome': {'label': 'Cliente', 'required': True},
        'cliente_telefone': {'label': 'Telefone', 'required': True},
        'data_pedido': {'type': 'DATA_HORA'},
        'status': {'type': 'LIST', 'options': QUOTE_STATUS},
        'validade': {'type': 'INT', 'default': 3},
        'carteira_id': {'type': 'FK'},
        'forminhas': {'type': 'LIST', 'options': FORMINHAS},
        'observacao': {'type': 'MEMO'},
        'pedido_id': {'type': 'ID'},
    },
    'OrcamentoItem': {
        'produto_id': {'type': 'FK'},
        'qtd': {'type': 'INT', 'required': True},
        'preco': {'type': 'NUM', 'currency': 'brl'},
        'observacao': {'type': 'TEXT'},
    },
    'Evento': {
        'tipo': {'type': 'LIST', 'options': tipos_evento},
        'tema': {'type': 'TEXT'},
        'obs': {'type': 'MEMO'},
        'data': {'type': 'DATA'},
        'hora': {'type': 'HORA'},
        'local': {'type': 'TEXT'},
        'convidados': {'type': 'INT'},
        'cerimonial': {'type': 'TEXT'},
    },
}


def _notificar_orcamento(quote):
    """Notificação ntfy para a doceira (falha silenciosa sem topic configurado)."""
    topic = Configuracao.get("ntfy_topic")
    if not topic:
        return

    cliente = quote.cliente_nome or "?"
    telefone = quote.cliente_telefone or "?"

    items = []
    for item in quote.items:
        nome = item.produto.nome if item.produto else "?"
        items.append(f"- {item.qtd}x {nome}")

    event = quote.evento
    extra = ""
    if event:
        if event.tipo:
            extra += f" | {event.tipo}"
        if event.data:
            extra += f" | {event.data.strftime('%d/%m')}"

    title = "Algodoce recebeu um novo orçamento"
    message = f"Cliente: {cliente}\nFone: {telefone}{extra}\n" + "\n".join(items)

    aj_notificar(
        topic=topic,
        title=title,
        message=message,
        tags=["envelope"],
        token=Configuracao.get("ntfy_token"),
    )


def _on_send_orcamento(quote):
    """Evento pós-envio da página: notifica e limpa o carrinho/identificação."""
    _notificar_orcamento(quote)
    session.pop(CART_SESSION_KEY, None)
    session.pop(CLIENT_SESSION_KEY, None)


Page = {
    'type': 'cart',
    'max_width': 48,
    'props': {
        'on_send': _on_send_orcamento,
        'sessions': {
            'Itens do Orçamento': {'type': 'table', 'fields': 'OrcamentoItem'},
            'Dados do Evento': {'type': 'form', 'fields': 'Evento'},
        },
    },
}


def _mod():
    return sys.modules[__name__]


@auto.rota("/remover/<int:id>", methods=["POST"], endpoint="remover")
def remover(id):
    sc = resolve_cart(_mod())
    items = session.get(sc['session_key'], [])
    session[sc['session_key']] = [
        i for i in items if i.get(sc['item_id']) != id
    ]
    return redirect(url_for(f'{request.endpoint.rsplit(".", 1)[0]}.list'))


@auto.rota("/atualizar-item", methods=["POST"], endpoint="atualizar_item")
def atualizar_item():
    sc = resolve_cart(_mod())
    data = request.get_json(silent=True) or {}
    produto_id = data.get(sc['item_id'])
    if not produto_id:
        return jsonify(error='produto_id required'), 400

    if 'quantidade' in data:
        try:
            quantidade = int(data['quantidade'])
        except (TypeError, ValueError):
            return jsonify(error='Quantidade inválida.'), 400
        produto = sc['origin_model'].query.get(produto_id)
        if produto is None:
            return jsonify(error='Produto não encontrado.'), 404
        minima = minimo_quantidade(sc, produto)
        if quantidade < minima:
            return jsonify(
                error=f'A quantidade mínima para {produto.nome} é {minima} und.'
            ), 400

    items = session.get(sc['session_key'], [])
    for i in items:
        if i.get(sc['item_id']) == produto_id:
            if 'quantidade' in data:
                i['quantidade'] = quantidade
            if 'observacao' in data:
                i['observacao'] = data['observacao'].strip() or None
            break
    session[sc['session_key']] = items
    return jsonify(success=True)


@auto.rota("/enviar", methods=["POST"], endpoint="enviar")
def enviar():
    return send_cart(_mod())


@auto.rota("/api/orcamento-count", endpoint="orcamento_count")
def orcamento_count():
    sc = resolve_cart(_mod())
    return jsonify(total=count_items(sc))
