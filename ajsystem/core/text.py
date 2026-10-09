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

# Passadas extras para um rótulo de catálogo que traz `{campo}` dentro dele
# (frase de documento). Um catálogo que se referencia sai no limite.
LABEL_DEPTH = 3


def dotted_get(obj, path):
    """getattr encadeado com navegação segura (None no meio -> None)."""
    cur = obj
    for part in (path or '').split('.'):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


# `when` com expressão: `or`/`and`/`not` sobre paths, mais comparação. Precedência
# NOT > AND > OR, e as duas grafias — `or`/`and`/`not` e `|`/`&`/`!` — valem. Parser
# próprio em vez de `eval`: o avaliador de `calc` (`do_report._calc_fn`) usa `eval`
# porque é aritmética com namespace montada, e trazer isso para cá abriria execução
# de código num módulo genérico que list/select também usam.
_OR_RE = re.compile(r'\s+(?:or|\|\|?)\s+|\|\|?')
_AND_RE = re.compile(r'\s+(?:and|&&)\s+|&')
_NOT_RE = re.compile(r'^(?:not\s+|!)', re.I)
# Comparação: `caminho OP valor`. As alternativas mais longas primeiro — sem isso
# `>=` casaria `>` e sobraria `=` para ser lido como path. O lado direito é literal
# (número ou string entre aspas) ou outro path, que resolve pelo mesmo `dotted_get`.
_CMP_RE = re.compile(
    r'^([\w.]+)\s*(>=|<=|==|!=|<>|<|>|=)\s*'
    + r"""('[^']*'|"[^"]*"|-?\d+(?:\.\d+)?|True|False|None|[\w.]+)$""")
# Sobrou operador que não virou comparação: `'status >> 0'`, `'a >'`, `'> 0'`.
# Sem este erro, o resto caía em `dotted_get`, que devolve None para um path
# inexistente — e o documento saía silenciosamente errado em vez de reclamar.
_OP_LEFTOVER_RE = re.compile(r'[<>!=]=?|[<>]')

_CMP_FUNCS = {
    '>': lambda a, b: a > b, '>=': lambda a, b: a >= b,
    '<': lambda a, b: a < b, '<=': lambda a, b: a <= b,
    '=': lambda a, b: a == b, '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b, '<>': lambda a, b: a != b,
}


def _cmp_operand(tok, obj):
    """Lado direito da comparação: literal, ou path se não for literal."""
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ('"', "'"):
        return tok[1:-1]
    if tok == 'True':
        return True
    if tok == 'False':
        return False
    if tok == 'None':
        return None
    try:
        return int(tok) if tok.isdigit() else float(tok)
    except ValueError:
        return dotted_get(obj, tok)


def _unparenthesize(expr):
    while len(expr) > 1 and expr.startswith('(') and expr.endswith(')'):
        inner = expr[1:-1].strip()
        # só remove se o parêntese realmente envolve a expressão toda
        if inner.count('(') != inner.count(')'):
            break
        expr = inner
    return expr.strip()


def _split_topo(expr, pattern):
    """Divide no `pattern` só no nível de parêntese 0.

    O `re.split` puro quebrava dentro do parêntese: `(a or b) and c` cortava no
    `or` e tratava `(a` como um path — que não existe, então a expressão dava
    `False` sem erro nenhum. O parêntese era documentado como sintaxe e não
    fazia nada; aqui ele passa a valer de verdade.
    """
    out, buf, depth, i = [], [], 0, 0
    for m in pattern.finditer(expr):
        pedaco = expr[i:m.start()]
        buf.append(pedaco)
        depth += pedaco.count('(') - pedaco.count(')')
        if depth == 0:                     # operador de verdade: separa
            out.append(''.join(buf))
            buf = []
        else:                              # dentro de parêntese: é texto
            buf.append(m.group(0))
        i = m.end()
    resto = expr[i:]
    buf.append(resto)
    depth += resto.count('(') - resto.count(')')
    if depth:
        raise ValueError(f"when: parêntese desbalanceado em {expr!r}")
    out.append(''.join(buf))
    return [p for p in out if p.strip()]


def _truth(expr, obj):
    """Avalia a expressão booleana de um `when` sobre os paths do objeto.

    Precedência NOT > AND > OR > comparação (comparação liga mais forte que
    NOT, como no Python: `not status > 0` é `not (status > 0)`).
    """
    e = _unparenthesize(str(expr or ''))
    neg = _NOT_RE.match(e)
    if neg:
        return not _truth(e[neg.end():], obj)
    # Só desce quando o operador era mesmo de topo. Se todos os `or`/`and`
    # estavam dentro de parênteses, o split devolve a expressão inteira e
    # reprocessá-la seria recursão infinita.
    for _pat, _comb in ((_OR_RE, any), (_AND_RE, all)):
        if _pat.search(e):
            partes = _split_topo(e, _pat)
            if len(partes) > 1:
                return _comb(_truth(p, obj) for p in partes)
    m = _CMP_RE.match(e)
    if m:
        esq, op, dir_ = m.group(1), m.group(2), m.group(3)
        a, b = dotted_get(obj, esq), _cmp_operand(dir_, obj)
        if a is None or b is None:
            # Ausente não ordena: `None > 0` em Python é TypeError, e aqui a
            # linha inteira sumiria com um erro que ninguém veria. Ausente é
            # "não" para ordenação e segue a identidade para `==`/`!=` — que é o
            # que `x == None` quer dizer.
            if op in ('!=', '<>'):
                return a is not b
            if op in ('=', '=='):
                return a is b
            return False
        try:
            return bool(_CMP_FUNCS[op](a, b))
        except TypeError:
            raise ValueError(
                f"when: comparação '{esq} {op} {dir_}' é entre tipos "
                f"incomparáveis ({type(a).__name__} vs {type(b).__name__})")
    if _OP_LEFTOVER_RE.search(e):
        raise ValueError(f"when: comparação não reconhecida em {e!r}")
    v = dotted_get(obj, e)
    return bool(v) and v != ''


def eval_when(obj, when):
    """`when` = path (pontilhado, truthy) **ou** expressão sobre paths
    (`'a or b'`, `'a | b'`, `'not a'`, com parênteses e comparação
    `'status > 0'`) **ou** dict `{campo: valores}`.

    O dict é o mesmo formato que o Schema já usava (`{'ativo': True, 'tipo':
    [1, 2]}`), e com dicionário como alvo `{'status': FRASE}` quer dizer "só nos
    status que estão neste catálogo" — foi o que deixou o CATÁLOGO ser a única
    fonte da verdade em vez de um `if status not in (...)` em Python. Na forma
    dict o alvo é COMPARAÇÃO (`True` casa com campo booleano), não truthiness;
    para "algum destes" use a expressão (`'acrescimo or desconto'`), e para
    "maior que" a comparação (`'status > 0'`), que liga mais forte que `not`.
    Ausente = sempre.
    """
    if when is None:
        return True
    if isinstance(when, dict):
        for campo, alvo in when.items():
            v = dotted_get(obj, campo)
            if isinstance(alvo, dict):
                if v not in alvo:
                    return False
            elif isinstance(alvo, (list, tuple, set, frozenset)):
                if v not in alvo:
                    return False
            elif v != alvo:
                return False
        return True
    if not isinstance(when, str) or not when:
        raise ValueError(f"when deve ser path str, expressão ou dict, veio {when!r}")
    return _truth(when, obj)


def render(tpl, get, labels=None):
    """Monta o texto. get(campo)->valor; labels={campo: {valor: rótulo}}.

    O rótulo de catálogo pode ter `{campo}` dentro dele, e aí precisa de uma
    segunda passada: é assim que uma frase de documento vira catálogo (o status
    escolhe a frase, o motivo entra no meio dela). A segunda passada é limitada
    por `LABEL_DEPTH`, porque catálogo que se referencia sozinho existe e o
    `re.sub` não para sozinho.
    """
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
        out = _FIELD_RE.sub(_sub, t)
        # Só a segunda passada quando entrou rótulo de catálogo: sem isso, todo
        # template passa a pagar uma varredura à toa.
        if labels and out != t:
            for _ in range(LABEL_DEPTH - 1):
                novo = _FIELD_RE.sub(_sub, out)
                if novo == out:
                    break
                out = novo
        return out
    except (ValueError, KeyError):
        return t
