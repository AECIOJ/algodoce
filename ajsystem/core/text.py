"""Texto dinâmico — avaliador único de templates do framework.

Sintaxe (usada em select.calc, coluna text e group text):
  '{campo}'            -> valor com label do catálogo (LIST -> options)
  '{campo:02d}'        -> valor cru com format-spec (sem label)
  '{?campo:literal}'   -> inclui o literal (com seus placeholders) só se o
                          campo não for None/vazio (segmento condicional)

Genérico: recebe getter + mapa de labels; não conhece model nem relatório.
"""
import re

_COND_RE = re.compile(r'{\?(\w+):((?:[^{}]|\{[^{}]*\})*)}')
_FIELD_RE = re.compile(r'{(\w+)(?::([^{}]*))?}')


def render(tpl, get, labels=None):
    """Monta o texto. get(campo)->valor; labels={campo: {valor: rótulo}}."""
    labels = labels or {}

    def _cond(m):
        fld, lit = m.group(1), m.group(2)
        v = get(fld)
        return lit if v is not None and v != '' else ''

    t = _COND_RE.sub(_cond, tpl or '')

    def _val(name, spec):
        v = get(name)
        if v is None:
            return ''
        o = labels.get(name)
        if o is not None and not spec:
            v = o.get(v, v)
        if spec:
            try:
                return format(v, spec)
            except (ValueError, TypeError):
                return str(v)
        return str(v)

    def _sub(m):
        return _val(m.group(1), m.group(2) or '')

    try:
        return _FIELD_RE.sub(_sub, t)
    except (ValueError, KeyError):
        return t
