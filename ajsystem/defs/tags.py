"""TAG — badges semânticos por campo (camada de dados, padrão `Button`).

Unifica os antigos `Form.tags`/`List.tags` numa prop `Field.tag`. Uma `Tag`
descreve como o valor do campo vira um badge (texto + cor), de forma declarativa
e data-agnóstica. Onde renderizar é definido por `Field.pos_form: 4`
(barra do form) e `Field.pos_list: 4` (barra da listagem).
"""
from dataclasses import dataclass
from typing import Any, Optional


# ── Cores enumeradas 0–9 → nomes DaisyUI ───────────────────────────────────
# `colors` de uma Tag aceita `int` 0–9 como atalho para estes nomes.
COLORS_0_to_9 = {
    0: 'ghost', 1: 'primary', 2: 'secondary', 3: 'success', 4: 'warning',
    5: 'error', 6: 'info', 7: 'accent', 8: 'neutral', 9: 'base',
}


def _resolve_tag_color(value, options=None, colors=None, fixed=None):
    """Cor do badge por heurística (texto/número) com override `colors`.

    `colors` mapeia VALOR → cor NAMED ou índice 0–9 (resolvido aqui).
    `fixed` (cor fixa da Tag) tem precedência abaixo de `colors[valor]`
    e acima da heurística.
    """
    if colors and value in colors:
        c = colors[value]
        return COLORS_0_to_9[c] if isinstance(c, int) and c in COLORS_0_to_9 else c
    if fixed:
        return fixed
    if options and value in options:
        label = str(options[value]).lower()
    else:
        label = str(value).lower() if value is not None else ''
    if any(w in label for w in ('aprovado', 'renovado', 'ativo', 'pago', 'entregue')):
        return 'success'
    if any(w in label for w in ('reprovado', 'rejeitado', 'expirado', 'cancelado', 'inativo', 'atrasado')):
        return 'error'
    if any(w in label for w in ('negociação', 'negociacao', 'pendente', 'aguardando', 'enviado')):
        return 'warning'
    if any(w in label for w in ('rocessando', 'andamento', 'faturado')):
        return 'info'
    if isinstance(value, (int, float)):
        if value <= 2:
            return 'warning'
        if value <= 6:
            return 'info'
        return 'error'
    return 'ghost'


# ── Presets prontos (padrão `Button`) ───────────────────────────────────────
_PRESETS = {
    'boolean': {'colors': {True: 'success', False: 'ghost'}},
    'ativo': {'colors': {True: 'success', False: 'ghost'}},
    'status': None,  # heurística `_resolve_tag_color` (sem `colors`)
}


@dataclass
class Tag:
    """Badge de um campo. `colors` mapeia VALOR do campo → cor (named ou 0–9).

    `link` (endpoint, ex.: 'pedidos.form') torna o badge navegável
    (`url_for(link, id=valor)`). `color` fixa a cor do badge, com precedência
    abaixo de `colors[valor]` e acima da heurística.
    """
    colors: Optional[dict] = None
    preset: Optional[str] = None
    size: str = 'sm'
    outline: bool = False
    text_field: Optional[str] = None
    link: Optional[str] = None
    color: Optional[str] = None
    cls: str = ''

    def badge_cls(self, color: str) -> str:
        if self.cls:
            return self.cls
        base = f'badge badge-{color} badge-{self.size}'
        return base + (' badge-outline' if self.outline else '')


_TAG_KEYS = frozenset(Tag.__dataclass_fields__)


def parse_tag(spec: Any) -> Optional[Tag]:
    """Normaliza a prop `Field.tag` (True/str/dict) para `Tag` (ou None)."""
    if spec is None or spec is False:
        return None
    if isinstance(spec, Tag):
        return spec
    if spec is True:
        return Tag()
    if isinstance(spec, str):
        preset = _PRESETS.get(spec)
        if preset and preset.get('colors'):
            return Tag(colors=dict(preset['colors']), preset=spec)
        return Tag(preset='status')
    if isinstance(spec, dict):
        tag = Tag(**{k: v for k, v in spec.items() if k in _TAG_KEYS})
        preset = _PRESETS.get(tag.preset)
        if preset and preset.get('colors'):
            base = preset['colors']
            tag.colors = {**base, **(tag.colors or {})}
        return tag
    return None


def tag_text(value, options=None):
    """Rótulo exibido no badge: options.get(val, val) ou string do valor."""
    if options and value is not None:
        return str(options.get(value, value))
    return '' if value is None else str(value)


def resolve_tag(spec: Any, value, options=None, text_value=None):
    """Resolve `Field.tag` + valor do instance → dict `{text, color}` renderizável.

    É o núcleo compartilhado por form (`pos_form: 4`) e listagem (`pos_list: 4`).
    """
    tag = parse_tag(spec) if not isinstance(spec, Tag) else spec
    if tag is None:
        return None
    text = text_value if text_value is not None else tag_text(value, options)
    color = _resolve_tag_color(value, options, tag.colors, tag.color)
    return {'text': text, 'color': color, 'link': tag.link, 'tag': tag}