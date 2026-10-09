"""Avaliador de expressão do framework — o ÚNICO lugar que avalia expressão.

Cobre, com uma gramática só:

- **paths** pontilhados (`valor`, `a.b.c`) — o que resolve é `obj`/`get`;
- **literais**: número, string entre aspas, `True`/`False`/`None`;
- **aritmética** `+ - * / // %` e unário `+`/`-`, com parêntese;
- **comparação** `>`, `>=`, `<`, `<=`, `==`, `!=`, `=` e `<>`;
- **booleano** `and`/`or`/`not`, e as grafias `&`, `|`, `||`, `!`;
- **chamada** de função, e só da allowlist que o caller passa (`funcoes=`).

Existe para que `when`, o ternário do template, o `calc` da Entity e o
`calc_value` da list compartilhem a MESMA gramática. Antes eram dois mundos:
`_truth` (parser próprio, booleano) e `eval` do Python (aritmética com
namespace montado) — o que fazia o mesmo conceito ter duas sintaxes e dois
conjuntos de bug.

Não é Python. Parser próprio, recursivo descendente, sem `exec`/`eval`: o
módulo é genérico (list, select, report e o app usam), e `eval` aqui abriria
execução de código num lugar onde não há motivo para isso. O que ele não sabe,
ele diz — função fora da allowlist e operador desconhecido levantam nomeando a
expressão, em vez de virar `None` calado.

Precedência, do mais fraco ao mais forte (a do Python):
`or` < `and` < `not` < comparação < `+ -` < `* / // %` < unário < primário.
"""
import re

__all__ = ['avaliar', 'condicao', 'dotted_get']


def dotted_get(obj, path):
    """getattr encadeado com navegação segura (None no meio -> None)."""
    cur = obj
    for part in (path or '').split('.'):
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


# Tokenizador: `num` e `str` antes de `name`, e os operadores de 2 caracteres
# antes dos de 1 — senão `>=` viraria `>` e sobrasse `=`.
_TOKEN_RE = re.compile(r"""
    \s*(?:
      (?P<num>\d+\.\d+|\d+)
    | (?P<str>'[^']*'|"[^"]*")
    | (?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
    | (?P<op>//|>=|<=|==|!=|<>|[-+*/%<>=|&!(),])
    )
""", re.X)

# Grafia dupla aceita por herança do `when`: `|`, `||`, `&`, `!`.
_BIN_OR = ('or', '|', '||')
_BIN_AND = ('and', '&')
_CMP = {
    '>': lambda a, b: a > b, '>=': lambda a, b: a >= b,
    '<': lambda a, b: a < b, '<=': lambda a, b: a <= b,
    '=': lambda a, b: a == b, '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b, '<>': lambda a, b: a != b,
}
_ADD = ('+', '-')
_MUL = ('*', '/', '//', '%')
_NEG = ('-', '+')


def _tokeniza(expr, rotulo):
    toks, i, n = [], 0, len(expr)
    while i < n:
        m = _TOKEN_RE.match(expr, i)
        if not m or m.end() == i:
            raise ValueError(f"{rotulo}: não reconheci {expr[i:]!r} em {expr!r}")
        i = m.end()
        if m.group('num') is not None:
            txt = m.group('num')
            toks.append(('num', float(txt) if '.' in txt else int(txt)))
        elif m.group('str') is not None:
            toks.append(('txt', m.group('str')[1:-1]))
        elif m.group('name') is not None:
            # `and`/`or`/`not` casam como nome (o regex de identificador é mais
            # largo), e viram operador aqui — senão todo `_come(_BIN_OR)` falha
            # e a expressão morre em "sobrou 'or'". Nenhum campo do framework se
            # chama assim: são palavra-chave do Python.
            nome = m.group('name')
            toks.append(('op', nome) if nome in ('and', 'or', 'not') else ('name', nome))
        else:
            toks.append(('op', m.group('op')))
    return toks


class _Parser:
    """Descida recursiva. `ler` resolve path; `funcoes` é a allowlist."""

    def __init__(self, toks, ler, funcoes, expr, rotulo):
        self.t, self.i = toks, 0
        self.ler, self.funcoes = ler, funcoes or {}
        self.expr, self.rotulo = expr, rotulo

    def _erro(self, msg):
        return ValueError(f"{self.rotulo}: {msg} em {self.expr!r}")

    def _peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def _e_operador(self, ops):
        k, v = self._peek()
        return k == 'op' and v in ops

    def _come(self, ops):
        if self._e_operador(ops):
            self.i += 1
            return True
        return False

    def parse(self):
        v = self._ou()
        if self.i < len(self.t):
            raise self._erro(f"sobrou {self.t[self.i][1]!r}")
        return v

    def _ou(self):
        v = self._e()
        while self._come(_BIN_OR):
            # `or`/`and` devolvem o OPERANDO, como no Python (e não um bool
            # forçado): `'a or b'` com `a` vazio tem que valer `b`.
            d = self._e()
            v = v if v else d
        return v

    def _e(self):
        v = self._nao()
        while self._come(_BIN_AND):
            # Python: `a and b` devolve `a` se `a` é falso, senão `b`. Inverter
            # isso (devolvendo `a` quando é verdade) faz `x > 0 and y > 5` valer
            # `True` com `y` falso — e uma condição que mente calada é o pior
            # bug que existe.
            d = self._nao()
            v = d if v else v
        return v

    def _nao(self):
        # `not` fica ACIMA da comparação (o que o Python faz: `not status > 0`
        # é `not (status > 0)`). Se ficasse no primário viraria `(not status) > 0`,
        # que é sempre falso e nunca reclama.
        k, v = self._peek()
        if (k == 'op' and v in ('not', '!')):
            self.i += 1
            return not self._nao()
        return self._compara()

    def _compara(self):
        a = self._aditiva()
        k, op = self._peek()
        if k == 'op' and op in _CMP:
            self.i += 1
            b = self._aditiva()
            return self._aplica_cmp(op, a, b)
        return a

    def _aplica_cmp(self, op, a, b):
        if a is None or b is None:
            # Ausente não ordena: `None > 0` em Python é TypeError, e o efeito
            # aqui seria a linha INTEIRA sumir sem erro visível. Ausente é
            # "não" para ordenação e segue a identidade em `==`/`!=` — que é o
            # que `x == None` quer dizer.
            if op in ('!=', '<>'):
                return a is not b
            if op in ('=', '=='):
                return a is b
            return False
        try:
            return bool(_CMP[op](a, b))
        except TypeError:
            raise self._erro(
                f"comparação '{op}' entre tipos incomparáveis "
                f"({type(a).__name__} vs {type(b).__name__})")

    def _aditiva(self):
        v = self._multiplicativa()
        while self._e_operador(_ADD):
            op = self.t[self.i][1]
            self.i += 1
            d = self._multiplicativa()
            try:
                v = v + d if op == '+' else v - d
            except TypeError:
                raise self._erro(f"'{op}' entre {type(v).__name__} e {type(d).__name__}")
        return v

    def _multiplicativa(self):
        v = self._unaria()
        while self._e_operador(_MUL):
            op = self.t[self.i][1]
            self.i += 1
            d = self._unaria()
            try:
                v = {'*': lambda a, b: a * b, '/': lambda a, b: a / b,
                     '//': lambda a, b: a // b, '%': lambda a, b: a % b}[op](v, d)
            except ZeroDivisionError:
                raise self._erro(f"divisão por zero em {op!r}")
            except TypeError:
                raise self._erro(f"'{op}' entre {type(v).__name__} e {type(d).__name__}")
        return v

    def _unaria(self):
        k, v = self._peek()
        if k == 'op' and v in _NEG:
            self.i += 1
            d = self._unaria()
            return -d if v == '-' else +d
        return self._primario()

    def _primario(self):
        k, v = self._peek()
        if k is None:
            raise self._erro('expressão acaba no meio')
        if k == 'num':
            self.i += 1
            return v
        if k == 'txt':
            self.i += 1
            return v
        if k == 'op' and v == '(':
            self.i += 1
            r = self._ou()
            if not self._come((')',)):
                raise self._erro("esperava ')'")
            return r
        if k == 'name':
            self.i += 1
            if v == 'True':
                return True
            if v == 'False':
                return False
            if v == 'None':
                return None
            if v == 'not':
                return not self._unaria()
            if v in _BIN_OR:                 # `or`/`and` sem operando à esquerda
                raise self._erro(f"operador {v!r} sem lado esquerdo")
            if self._e_operador(('(',)):
                return self._chamada(v)
            return self.ler(v)
        raise self._erro(f"token inesperado {v!r}")

    def _chamada(self, nome):
        self.i += 1                                   # '('
        fn = self.funcoes.get(nome)
        if fn is None:
            raise self._erro(
                f"função {nome!r} fora da allowlist {sorted(self.funcoes)}")
        args = []
        if not self._e_operador((')',)):
            args.append(self._ou())
            while self._come((',',)):
                args.append(self._ou())
        if not self._come((')',)):
            raise self._erro(f"esperava ')' fechando {nome}(")
        try:
            return fn(*args)
        except TypeError:
            raise self._erro(f"{nome}() com {len(args)} argumento(s)")


def avaliar(expr, obj=None, get=None, funcoes=None, rotulo='expressão'):
    """Avalia `expr` e devolve o VALOR.

    `obj` é lido com `dotted_get`; `get` (um getter de uma chave) tem precedência
    e é o que o template usa, que não tem objeto. `funcoes` é a allowlist de
    chamada. `rotulo` só muda o que o erro nomeia (`'when'`, `'calc'`).
    """
    txt = str(expr or '').strip()
    if not txt:
        return None
    ler = get if get is not None else (lambda path: dotted_get(obj, path))
    return _Parser(_tokeniza(txt, rotulo), ler, funcoes, txt, rotulo).parse()


def condicao(expr, obj=None, get=None, rotulo='when'):
    """`avaliar` + a verdade: Ausente é "não" (e `''` também), como o `when`."""
    v = avaliar(expr, obj, get, rotulo=rotulo)
    return bool(v) and v != ''