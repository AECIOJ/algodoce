"""Spec `showcase` — vocabulário da vitrine declarativa (camada de dados).

Página única declarada por `Page['showcase']`. Este módulo é a camada de dados
pura (sem modelos, request nem motor): registra os termos do modal de
identificação de cliente, os layouts e as posições de card, e resolve as
partes da config que não dependem de runtime.

Config:

    showcase = {
        'fields': 'Product',     # entidade dos itens (chave do `Entity` do módulo)
        'filter': 'Category',    # entidade do filtro por categoria (opcional)
        'layout': 'carousel',    # 'carousel' | 'grid' | 'list'
        'show': {                # campos exibidos e posição no card
            'nome':       'title',
            'descricao':  'left',
            'imagem':     'right',
            'qtd_minima': 'qty',
        },
        'client_fields': ['nome', 'telefone'],   # termos do modal de identificação
        'badge_id': 'bnOrcamentoBadge',          # id no shell p/ o contador do carrinho
    }
"""

import re

# Termos de identificação de cliente: token → {input, label, required, mask}.
# O modal é renderizado pelo motor a partir dos termos presentes em
# `client_fields`; termos novos entram neste registro.
CLIENT_FIELD_DEFS = {
    'nome':     {'input': 'text',  'label': 'Nome',               'required': True,  'mask': None},
    'telefone': {'input': 'tel',   'label': 'Telefone (com DDD)', 'required': True,  'mask': 'phone'},
    'email':    {'input': 'email', 'label': 'E-mail',             'required': False, 'mask': None},
}

CLIENT_FIELD_ALIASES = {
    'fone': 'telefone',
    'mail': 'email',
}

# Layouts de apresentação da vitrine (template `pages/showcase.html`).
SHOWCASE_LAYOUTS = ('carousel', 'grid', 'list')

# Posições de card preenchidas por `show` (extensível).
SHOWCASE_POSITIONS = ('title', 'left', 'right', 'qty')

# Chaves da session controladas pelo motor.
CART_SESSION_KEY = 'cart_items'
CLIENT_SESSION_KEY = 'client'

# Default de `item_id` dentro de cada item do carrinho (deriva da entidade).
def item_id_default(entity_name: str) -> str:
    """`'Product'` → `'product_id'` (chave do id dentro do item do carrinho)."""
    key = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name or '').lower()
    return f'{key}_id' if key else 'id'


def resolve_client_field(token):
    """Resolve um termo de `client_fields` para a config do input (com alias)."""
    token = (token or '').strip().lower()
    token = CLIENT_FIELD_ALIASES.get(token, token)
    return CLIENT_FIELD_DEFS.get(token)


def resolve_client_fields(tokens):
    """Resolve a lista de termos p/ as configs dos inputs do modal.

    Levanta `ValueError` para termo desconhecido (falha rápida na montagem).
    """
    result = []
    for t in tokens or []:
        cfg = resolve_client_field(t)
        if cfg is None:
            raise ValueError(f"SHOWCASE: termo de cliente desconhecido: {t!r}")
        result.append({'token': t, **cfg})
    return result


def resolve_show(cfg):
    """Valida `show` ({campo: posição}) e devolve lista ordenada (campo, posição).

    A ordem do dict define a ordem no card; cada posição é do vocabulário
    `SHOWCASE_POSITIONS`. Levanta `ValueError` para posição desconhecida.
    """
    show = cfg.get('show') or {}
    if not isinstance(show, dict):
        raise ValueError("SHOWCASE: 'show' deve ser um dict {campo: posição}")
    result = []
    for campo, pos in show.items():
        if pos not in SHOWCASE_POSITIONS:
            raise ValueError(
                f"SHOWCASE: posição inválida {pos!r} para {campo!r} "
                f"(válidas: {', '.join(SHOWCASE_POSITIONS)})"
            )
        result.append((campo, pos))
    return result
