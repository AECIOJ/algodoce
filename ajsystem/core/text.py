"""Texto dinâmico — avaliador único de templates do framework.

Sintaxe (usada em select.calc, coluna text, group text e items):
  '{campo}'            -> valor com label do catálogo (LIST -> options)
  '{a.b.c}'            -> path pontilhado com navegação segura (None -> '')
  '{campo:02d}'        -> valor cru com format-spec (sem label)
  '{valor:brl}'        -> moeda BRL (R$ 1.234,56)
  '{campo|padrao}'     -> literal quando None/vazio (ex. fallback)
  '{?campo:literal}'   -> inclui o literal (com seus placeholders) só se o
                          campo não for None/vazio (segmento condicional)
  '{cond ? a : b}'     -> `a` se a expressão `cond` for verdadeira (a MESMA
                          gramática do `when`: paths, comparação, and/or/not,
                          parênteses), senão `b`. Os ramos podem ter `{campo}`
                          e aninhamento é entre chaves: `{c ? x : {c2 ? y : z}}`

Genérico: recebe getter + mapa de labels; não conhece model nem relatório.
"""
import re

_COND_RE = re.compile(r'{\?([\w.]+):((?:[^{}]|\{[^{}]*\})*)}')
_FIELD_RE = re.compile(r'{([\w.]+)(?::([^{}|]*))?(?:\|([^{}]*))?}')

# Passadas extras para um rótulo de catálogo que traz `{campo}` dentro dele
# (frase de documento). Um catálogo que se referencia sai no limite.
LABEL_DEPTH = 3


# `dotted_get` vive em `core/expr.py` (mesma leitura de path do avaliador) e
# continua exportado aqui: `pdf.py` e `do_report.py` importam deste módulo.
from ajsystem.core.expr import dotted_get  # noqa: E402,F401

import datetime as _dt
# `datetime` é subclasse de `date`, então os três cabem num `isinstance`.
_DT_TYPES = (_dt.datetime, _dt.date, _dt.time)


# A expressão booleana (`when`, ternário) e a aritmética (`calc`) são a MESMA
# gramática, e ela mora em `core/expr.py`: um avaliador só para o framework. Era
# dois — `_truth` aqui (parser próprio, booleano) e `eval` do Python em
# `do_report._calc_fn`/`utils.calc_value` (aritmética com namespace montado) —
# com duas sintaxes e dois conjuntos de bug para o mesmo conceito.
from ajsystem.core.expr import avaliar as _avaliar, condicao as _condicao  # noqa: E402


def _truth(expr, obj=None, get=None):
    """Avalia a expressão booleana de um `when` sobre os paths do objeto.

    Compatibilidade: a gramática é a de `core/expr.condicao`, com a mesma
    precedência (OR < AND < NOT < comparação) e os mesmos casos de ausente.
    """
    return _condicao(expr, obj, get, rotulo='when')


# ── Ternário no template ────────────────────────────────────────────────────
# `{cond ? a : b}` escolhe `a` ou `b` pela MESMA gramática do `when`
# (paths, comparação, and/or/not, parênteses) — um mecanismo só, não dois.
#
# Scanner, e não regex: o ramo pode conter `{campo}` e `:` de format-spec
# (`{qtd:02d}`), e o que separa os ramos é o `?`/`:` de nível 0. Regex não
# distingue os dois, e o resultado errado aqui é texto trocado por outro texto
# — o pior tipo de bug, porque sai bonito.
def _fecha(tpl, i):
    """Índice do `}` que fecha o `{` em `i` (None se não fechar)."""
    prof = 0
    for j in range(i, len(tpl)):
        if tpl[j] == '{':
            prof += 1
        elif tpl[j] == '}':
            prof -= 1
            if prof == 0:
                return j
    return None


def _pos_topo(texto, alvo):
    """Primeira posição do caractere no nível 0 (fora de `{...}`), ou -1."""
    prof = 0
    for j, ch in enumerate(texto):
        if ch == '{':
            prof += 1
        elif ch == '}':
            prof -= 1
        elif ch == alvo and prof == 0:
            return j
    return -1


def _ternarios(tpl, get):
    """Resolve `{cond ? a : b}` recursivo, leaving os outros `{...}` intactos."""
    out, i, n = [], 0, len(tpl or '')
    while i < n:
        if tpl[i] != '{':
            out.append(tpl[i])
            i += 1
            continue
        fim = _fecha(tpl, i)
        if fim is None:                    # abre sem fechar: não é nosso
            out.append(tpl[i:])
            break
        dentro = tpl[i + 1:fim]
        # `{?campo:literal}` é a forma de segmento condicional, não ternário.
        pos = -1 if dentro.startswith('?') else _pos_topo(dentro, '?')
        if pos < 0:
            out.append(tpl[i:fim + 1])     # `{campo}`, `{a:spec}`, `{?x:y}`: fica
            i = fim + 1
            continue
        resto = dentro[pos + 1:]
        sep = _pos_topo(resto, ':')
        if sep < 0:
            raise ValueError(f"ternário sem ':' em {{{dentro}}}")
        # O espaço em volta de `?` e `:` é separador, não conteúdo: sem este
        # strip o ramo saía como ' Pedido ' e o título levava espaço sobrando.
        a, b = resto[:sep].strip(), resto[sep + 1:].strip()
        for nome, ramo in (('a', a), ('b', b)):
            if _pos_topo(ramo, '?') >= 0 or _pos_topo(ramo, ':') >= 0:
                raise ValueError(
                    f"ternário: ramo {nome} de {{{dentro}}} tem '?' ou ':' "
                    f"no nível 0 — aninhe entre chaves: "
                    f"{{c ? x : {{c2 ? y : z}}}}")
        out.append(_ternarios(a if _condicao(dentro[:pos].strip(), get=get) else b, get))
        i = fim + 1
    return ''.join(out)


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


def render(tpl, get, labels=None, masks=None):
    """Monta o texto. get(campo)->valor; labels={campo: {valor: rótulo}};
    masks={campo: máscara}, que entra como spec padrão quando o campo não traz
    spec próprio.

    O rótulo de catálogo pode ter `{campo}` dentro dele, e aí precisa de uma
    segunda passada: é assim que uma frase de documento vira catálogo (o status
    escolhe a frase, o motivo entra no meio dela). A segunda passada é limitada
    por `LABEL_DEPTH`, porque catálogo que se referencia sozinho existe e o
    `re.sub` não para sozinho.
    """
    labels = labels or {}
    masks = masks or {}

    # Ternário ANTES de tudo: o ramo escolhido pode ter `{campo}`, que entra
    # nas passadas seguintes com o catálogo já aplicado.
    t = _ternarios(tpl or '', get)

    def _cond(m):
        fld, lit = m.group(1), m.group(2)
        v = get(fld)
        return lit if v is not None and v != '' else ''

    t = _COND_RE.sub(_cond, t)

    def _val(name, spec, default):
        v = get(name)
        if v is None or v == '':
            return default if default is not None else ''
        o = labels.get(name)
        # A máscara da Entity entra como spec PRÓPRIO DEFAULT: só quando o
        # template não deu spec. Passa pela gramática de máscara (`dd/mm/yyyy`),
        # e não pelo `format()` do Python — `format(datetime, 'dd/mm/yyyy')`
        # não existe, e era por isso que `{data}` imprimia o `repr` cru.
        # `spec` chega como '' quando o campo não traz spec próprio (o `_sub`
        # passa `m.group(2) or ''`) — então o teste é por FALSY, não por None.
        _m = masks.get(name)
        if not spec and _m:
            spec = _m
        if o is not None and not spec:
            v = o.get(v, v)
        if spec:
            # Valor de DATA/DATA-HORA/HORA com spec que não é `brl` vai pela
            # gramática de MÁSCARA, não pelo `format()` do Python — é o que faz
            # `{d:dd/mm/yyyy}` existir, já que `format(datetime, 'dd/mm/yyyy')`
            # não existe. Os outros tipos seguem no `format()` normal, para o
            # `{n:>10}` de um número continuar significando o que sempre significou.
            if spec != 'brl' and isinstance(v, _DT_TYPES):
                from ajsystem.core.formats import format as _fmt
                return _fmt(v, spec)
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
        # Só a segunda passada quando entrou rótulo de catálogo ou uma máscara
        # que devolveu texto com `{campo}` dentro: sem isso, todo template passa
        # a pagar uma varredura à toa.
        if (labels or masks) and out != t:
            for _ in range(LABEL_DEPTH - 1):
                novo = _FIELD_RE.sub(_sub, out)
                if novo == out:
                    break
                out = novo
        return out
    except (ValueError, KeyError):
        return t
