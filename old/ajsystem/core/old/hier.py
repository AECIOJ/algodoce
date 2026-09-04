"""Códigos hierárquicos em uma passada — emulação de window function.

`codigos(rows, ...)` percorre o conjunto UMA vez e atribui o código em
cada linha (setattr), equivalendo a:

    ROW_NUMBER() OVER (PARTITION BY <pai> ORDER BY <order>) por nível,
    encadeado via DFS a partir das raízes.

- `prefix_fields`  campos literais iniciais (ex.: `('tipo',)`) — valor
  direto da linha, formatado pelas primeiras larguras da máscara;
  None → omitido.
- `mask`           '9.99.99' — nº de 9s = dígitos do segmento (zero-pad);
  níveis além da máscara herdam a última largura.

Retorna as linhas em ordem DFS (prontas para exibição/relatório).
"""
from types import SimpleNamespace


def _widths(mask, n):
    w = [len(s) for s in mask.split('.')]
    return w + [w[-1]] * max(0, n - len(w))


def _fmt(value, width):
    try:
        return f'{int(value):0{width}d}'
    except (TypeError, ValueError):
        return str(value)[:width] if value not in (None, '') else ''


def _sort_key(order):
    def key(x):
        return tuple((getattr(x, a) is None, getattr(x, a) or 0)
                     for a in order)
    return key


def codigos(rows, attr='indice', *, prefix_fields=(), parent='pai_id',
            order=('ordem', 'id'), scope_fields=(), mask='9.99.99',
            sep='.'):
    rows = list(rows)
    sc_f = [scope_fields] if isinstance(scope_fields, str) else list(scope_fields)
    order_key = _sort_key(order)

    scopes = {}
    for r in rows:
        k = tuple(getattr(r, f, None) for f in sc_f)
        scopes.setdefault(k, []).append(r)

    out = []
    for skey in sorted(scopes, key=lambda k: tuple((x is None, x) for x in k)):
        members = scopes[skey]
        base = [getattr(members[0], f, None) for f in sc_f]

        roots, children = [], {}
        for r in members:
            pid = getattr(r, parent, None)
            if pid is None:
                roots.append(r)
            else:
                children.setdefault(pid, []).append(r)
        roots.sort(key=order_key)

        pfx_w = _widths(mask, len(prefix_fields))[:len(prefix_fields)]
        lvl_w = _widths(mask, 8)[len(prefix_fields):]

        def code_for(parts):
            cp = [_fmt(v, w) for v, w in zip(base + parts, pfx_w + lvl_w)]
            return sep.join(p for p in cp if p != '')

        def walk(node, parts):
            setattr(node, attr, code_for(parts))
            out.append(node)
            kids = sorted(children.get(getattr(node, 'id'), []), key=order_key)
            for j, ch in enumerate(kids, 1):
                walk(ch, parts + [j])

        for i, rt in enumerate(roots, 1):
            walk(rt, [i])
    return out
