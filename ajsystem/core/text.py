"""Texto dinâmico — avaliador único de templates do framework.

Sintaxe (usada em select.calc, coluna text, group text e items):
  '{campo}'            -> valor com label do catálogo (LIST -> options)
  '{a.b.c}'            -> path pontilhado com navegação segura (None -> '')
  '{campo:02d}'        -> valor cru com format-spec (sem label)
  '{valor:brl}'        -> moeda BRL (R$ 1.234,56)
  '{campo|padrao}'     -> literal quando None/vazio (ex. fallback)
  '{?campo:literal}'   -> inclui o literal (com seus placeholders) só se o
                          campo não for None/vazio (segmento condicional)

Genérico: recebe getter + mapa de labels; não conhece model nem relatório.
"""
import re

_COND_RE = re.compile(r'{\?([\w.]+):((?:[^{}]|\{[^{}]*\})*)}')
_FIELD_RE = re.compile(r'{([\w.]+)(?::([^{}|]*))?(?:\|([^{}]*))?}')


def dotted_get(obj, path):
    """getattr encadeado com navegação segura (None no meio -> None)."""
    cur = obj
    for part in (path or '').split('.'):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


def eval_when(obj, when):
    """when = path str avaliado truthy (pontilhado ok). Ausente = sempre."""
    if when is None:
        return True
    if not isinstance(when, str) or not when:
        raise ValueError(f"when deve ser path str, veio {when!r}")
    v = dotted_get(obj, when)
    return bool(v) and v != ''


def render(tpl, get, labels=None):
    """Monta o texto. get(campo)->valor; labels={campo: {valor: rótulo}}."""
    labels = labels or {}

    def _cond(m):
        fld, lit = m.group(1), m.group(2)
        v = get(fld)
        return lit if v is not None and v != '' else ''

    t = _COND_RE.sub(_cond, tpl or '')

    def _val(name, spec, default):
        v = get(name)
        if v is None or v == '':
            return default if default is not None else ''
        o = labels.get(name)
        if o is not None and not spec:
            v = o.get(v, v)
        if spec:
            if spec == 'brl':
                from ajsystem.core.formats import fmt_money as _fm
                try:
                    return _fm(v, True)
                except Exception:
                    return str(v)
            try:
                return format(v, spec)
            except (ValueError, TypeError):
                return str(v)
        return str(v)

    def _sub(m):
        return _val(m.group(1), m.group(2) or '', m.group(3))

    try:
        return _FIELD_RE.sub(_sub, t)
    except (ValueError, KeyError):
        return t
