"""Constantes genéricas do framework (sem dependência da aplicação host)."""

from datetime import date

CONNECTORS = {"de", "da", "do", "das", "dos", "para", "pra", "com", "sem", "em", "no", "na", "nos", "nas", "por", "ao", "aos", "à", "às", "e", "ou", "a", "o", "as", "os", "um", "uma", "uns", "umas", "num", "numa", "dum", "duma", "pelo", "pela", "pelos", "pelas", "pro", "pra", "pros", "pras"}

# LEGADO — moedas por código numérico. A moeda passou a vir da `mask`
# (`@M(id)`; `Field.currency` é derivada pelo motor e o dataclass não tem
# `currency`). `CURRENCY`/`DEFAULT_CURRENCY` ficam só como compatibilidade de
# `normalize_currency` (`1`/`True`/`'brl'` → padrão). `locale` segue o padrão
# BCP 47 para agrupamento decimal nos renderizadores.
CURRENCY = {
    0: None,
    1: {'symbol': 'R$', 'locale': 'pt-BR'},
    2: {'symbol': '$', 'locale': 'en-US'},
    3: {'symbol': '€', 'locale': 'pt-BR'},
}
DEFAULT_CURRENCY = 1

# Default de campo `data` em forms novos: callable (não congela no import).
TODAY = date.today


class _Predicado:
    """Predicado de valor sem estado, comparável por identidade (`is`).

    Espelha os predicados de `core/utils` (não sobrecarrega a palavra): a
    sentinela e o helper Python têm o mesmo sentido.
    """
    __slots__ = ('_nome',)

    def __init__(self, nome):
        self._nome = nome

    def __repr__(self):
        return self._nome

    __str__ = __repr__


# `NULL`/`NOT_NULL` ↔ `is_null` (só `None`, o NULL do banco).
# `EMPTY`/`NOT_EMPTY` ↔ `is_empty` (`None`, string em branco ou coleção vazia).
# Usados em `visible` (condição de dado) e em `filter.fixed` (condição SQL).
NULL = _Predicado('NULL')
NOT_NULL = _Predicado('NOT_NULL')
EMPTY = _Predicado('EMPTY')
NOT_EMPTY = _Predicado('NOT_EMPTY')


class _Grupo:
    """Nó de agrupamento booleano (`OR(...)`/`AND(...)`) para `filter.fixed`."""
    __slots__ = ('op', 'itens')

    def __init__(self, op, itens):
        self.op = op
        self.itens = itens

    def __repr__(self):
        return f"{self.op.upper()}({', '.join(repr(i) for i in self.itens)})"


def _grupo(op, itens):
    itens = list(itens)
    if not itens:
        raise ValueError(f"{op.upper()}(...): exige pelo menos uma condição")
    for it in itens:
        if not isinstance(it, (dict, _Grupo)):
            raise TypeError(
                f"{op.upper()}(...): cada item deve ser um dict (folhas) ou "
                f"outro OR(...)/AND(...); veio {type(it).__name__}")
    return _Grupo(op, itens)


def OR(*itens):
    """Agrupa condições com OU: `filter.fixed: OR({'a': NULL}, {'b': NULL})`."""
    return _grupo('or', itens)


def AND(*itens):
    """Agrupa condições com E (explícito; um dict já é AND por padrão)."""
    return _grupo('and', itens)


# Group Print
PRINT_NONE = 0      # não imprime rótulo do grupo / não imprime coluna
PRINT_ROW = 1       # imprime na célula da coluna, linha atual (default)
PRINT_INLINE = 2    # imprime no início da linha, avança para próxima
PRINT_TITLE = 3     # título do grupo, alinhado à esquerda
PRINT_TITLE_CENTER = 4  # título do grupo, centralizado
