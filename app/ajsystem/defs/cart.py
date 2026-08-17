"""Spec `cart` — vocabulário do carrinho declarativo (camada de dados).

Página única declarada por `Page['cart']`. O motor (`core/cart.py`) resolve as
sessões (tabela de itens + form de registro) a partir do `Entity` do módulo.

Config:

    cart = {
        'sessions': {
            'Itens do Orçamento': {'type': 'table', 'fields': 'QuoteItem'},
            'Dados do Evento':    {'type': 'form',  'fields': 'Event'},
        },
    }

Cada sessão referencia a entidade via `fields` (como `Form`/`List`); o modelo é
resolvido pelo motor pelo nome. A chave da sessão define o rótulo exibido.

Convenções (sem declaração):
- carrinho em `session['cart_items']` e identificação em `session['client']`,
  compartilhados com a vitrine (`showcase`) — mesma chave/estrutura de item;
- sessão `type: 'table'` → lida do carrinho de sessão. O pai (entidade
  principal) e a origem dos itens derivam das FKs do modelo da sessão;
- sessão `type: 'form'` → registro único lido do `request.form`; prefixo dos
  inputs = `snake_case(modelo) + '_'` (ex.: `Event` → `event_`); a FK que
  aponta para o pai é preenchida automaticamente;
- mínimo de quantidade = coluna `qtd_minima` do modelo de origem (default 1);
- `type` default = `'form'`.
"""
import re

from app.ajsystem.defs.showcase import CART_SESSION_KEY, CLIENT_SESSION_KEY

# Tipos de sessão do carrinho.
CART_SESSION_TYPES = ('table', 'form')

# Confirmação pós-envio (flash renderizado como overlay pelo shell do site).
CART_CONFIRM_FLASH = 'Orçamento enviado! Aguarde contato no WhatsApp.'

# Link de "incluir mais itens" / estado vazio (convenção: volta à vitrine).
CART_MORE_ITEMS_LINK = '/vitrine/'

# Título padrão da página do carrinho.
CART_TITLE = 'Meu Orçamento'


def field_prefix(entity_name: str) -> str:
    """`'Event'` → `'event_'` (snake_case do modelo + `_`)."""
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name or '').lower()
    return f'{key}_' if key else ''


def resolve_sessions(cfg):
    """Valida `sessions` e devolve lista ordenada de dicts.

    Cada sessão: `{'key', 'label', 'type', 'fields'}`. O `type` é do
    vocabulário `CART_SESSION_TYPES`; `fields` é o nome de uma entidade do
    módulo. Levanta `ValueError` para config inválida (falha rápida).
    """
    sessions = cfg.get('sessions') or {}
    if not isinstance(sessions, dict) or not sessions:
        raise ValueError("CART: 'sessions' deve ser um dict não-vazio")
    result = []
    for key, s in sessions.items():
        if not isinstance(s, dict):
            raise ValueError(f"CART: sessão {key!r} deve ser um dict")
        stype = s.get('type', 'form')
        if stype not in CART_SESSION_TYPES:
            raise ValueError(
                f"CART: type inválido {stype!r} em {key!r} "
                f"(válidos: {', '.join(CART_SESSION_TYPES)})"
            )
        fields = s.get('fields')
        if not fields or not isinstance(fields, str):
            raise ValueError(f"CART: sessão {key!r} precisa de 'fields' (entidade)")
        result.append({
            'key': key,
            'label': key,
            'type': stype,
            'fields': fields,
        })
    return result
