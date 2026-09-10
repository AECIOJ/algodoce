"""FORMATS — formatação e parse de valores (fonte única de formato).

Centraliza a "ida e volta" de valores ↔ strings:
- máscaras com tokens de data/hora (exibição via `fmt_mask`; parse via
  `_coerce_masked_datetime`), incluindo os derivados `ddd`/`mmm`;
- tokens de máscara alfanumérica `A` (só letra), `N` (letra/número),
  `#` (dígito, espaço ou sinal), caixa como digitada; forçar maiúscula via
  comando `@U`; comandos de máscara `@X` (`U/L/C/T` transform de texto,
  `R` remover separadores no save, `B/X` render de número em lista/readonly);
- números/moeda/percentual pt-BR (formatar e ler de volta);
- data/hora; transforms de texto (`title`/`upper`/`lower`/`cap`);
- validadores CPF/CNPJ.

Espelhado pelo cliente em `static/js/formats.js`. Os módulos antigos
(`defs.data`, `core.utils`, `defs.validators`, `defs.transformers`,
`core.form`) re-exportam daqui (shims) para não quebrar consumidores.
"""
import re
from datetime import date, datetime, time
from decimal import Decimal

from ajsystem.defs.constants import CONECTORES, CURRENCY, DEFAULT_CURRENCY

__all__ = [
    # mask display + tokens
    'has_date_tokens', 'fmt_mask', '_fmt_mask_data',
    'parse_mask_commands', 'mask_strip', 'fmt_mask_cmd', 'format',
    '_DOW_PT', '_MES_PT', '_DATE_TOKENS_RE',
    # mask parse
    '_coerce_masked_datetime', '_MASK_TOKENS', '_MASK_TEXT_TOKENS', '_MASK_TOKEN_ORDER',
    # números/moeda
    'parse_brl', 'fmt_brl', 'fmt_money', 'fmt_percent', 'fmt_num', 'fmt_id',
    'normalize_currency', 'currency_symbol',
    # data/hora
    'fmt_date', 'fmt_datetime', 'fmt_zero', 'fmt_zero_int',
    # transforms
    'apply_transform', 'apply_transform_value', '_title_case',
    # validadores
    'validar_cpf', 'validar_cnpj', 'VALIDATORS', 'resolve_validator',
]


# ── Tokens de máscara de data/hora ───────────────────────────────────────────
_DOW_PT = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']
_MES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
           'jul', 'ago', 'set', 'out', 'nov', 'dez']
_DATE_TOKENS_RE = re.compile(r'ddd|mmm|aaaa|yyyy|aa|yy|dd|mm|hh|ii|ss')


# Tokens alfanuméricos (comandos `@X` são prefixo; data/hora são minúsculos).
_ASCII_LETTERS = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')
_ASCII_DIGITS = frozenset('0123456789')
_ALPHA_TOKEN_RE = re.compile(r'[AN#]')


def _tok_match(ch, tok):
    """`ch` é aceito pelo token? 9=dígito; A=só letra; N=letra/número;
    #=dígito, espaço ou sinal (não-letra)."""
    if tok == '9':
        return ch in _ASCII_DIGITS
    if tok == 'A':
        return ch in _ASCII_LETTERS
    if tok == 'N':
        return ch in _ASCII_LETTERS or ch in _ASCII_DIGITS
    if tok == '#':
        return ch not in _ASCII_LETTERS
    return False


# Comandos de máscara (prefixo `@X`, letras maiúsculas em bloco: `@BX 999.99`).
_MASK_COMMANDS = {
    'U': 'upper', 'L': 'lower', 'C': 'cap', 'T': 'title',
    'R': 'R', 'B': 'B', 'X': 'X',
}
_TEXT_COMMANDS = ('U', 'L', 'C', 'T')


def parse_mask_commands(mask):
    """Separa os comandos `@X` (prefixo) do corpo da máscara.

    Ex.: '@BX 999,999.99' → (frozenset({'B', 'X'}), '999,999.99').
    Ex.: '@UR AAA-9A99' → ({'R', 'U'}, 'AAA-9A99').
    Validação fail-fast: comando desconhecido/literal `@` no corpo → ValueError.
    """
    if not mask:
        return frozenset(), ''
    s = str(mask).strip()
    cmds = []
    i = 0
    while i < len(s) and s[i] == '@':
        j = i + 1
        letters = []
        while j < len(s) and s[j] in _MASK_COMMANDS:
            letters.append(s[j])
            j += 1
        if not letters:
            ltr = s[i + 1:i + 2] or ''
            raise ValueError(f"MASK: comando desconhecido '@{ltr}' em '{mask}'")
        cmds.extend(letters)
        i = j
        if i < len(s) and s[i] == '@':
            continue
        break
    display = s[i:].lstrip(' \t')
    if display.startswith('@'):
        raise ValueError(f"MASK: comandos devem ser contíguos em '{mask}'")
    return frozenset(cmds), display


def _apply_text_cmds(text, cmds):
    """Aplica o transform de texto (U/L/C/T) presente em `cmds`, se houver."""
    for cmd in _TEXT_COMMANDS:
        if cmd in cmds:
            return apply_transform_value(text, _MASK_COMMANDS[cmd])
    return text


def has_date_tokens(mask):
    """Diz se a máscara tem tokens de data/hora (`dd`/`mm`/`mmm`/`aa`/`yy`/`aaaa`/`yyyy`/`ddd`/`hh`/`ii`/`ss`)."""
    if not mask:
        return False
    _, display = parse_mask_commands(mask)
    return _DATE_TOKENS_RE.search(display) is not None


def fmt_mask(value, mask):
    """Aplica `mask` a `value`. Tolerante: extrai os caracteres válidos antes.

    Prefixo `@X` (comandos `U/L/C/T`) é ignorado no posicionamento e aplicado
    ao texto final (para forçar maiúsculas use `@U`). Caminhos:
    - com tokens de data/hora e valor date/datetime/time → `_fmt_mask_data`
      (`dd`/`mm`/`aaaa`/`aa`/`yy`/`ddd`/`mmm`/`hh`/`ii`/`ss`; `9`s dos dígitos);
    - com tokens alfanuméricos `A`/`N`/`#` → `_fmt_mask_alpha`;
    - senão (máscara de dígitos `9` + literais) → caminho de dígitos.
    Sem corpo de máscara e valor sem data → `str(value)` com os comandos.
    """
    if value is None:
        return ''
    cmds, display = parse_mask_commands(mask)
    if display and has_date_tokens(display) and hasattr(value, 'strftime'):
        return _apply_text_cmds(_fmt_mask_data(value, display), cmds)
    if display and _ALPHA_TOKEN_RE.search(display):
        return _apply_text_cmds(_fmt_mask_alpha(value, display), cmds)
    if display:
        out = []
        di = 0
        digits = re.sub(r'\D', '', str(value))
        for ch in display:
            if ch == '9':
                if di < len(digits):
                    out.append(digits[di])
                    di += 1
                else:
                    break
            else:
                out.append(ch)
        return _apply_text_cmds(''.join(out), cmds)
    return _apply_text_cmds(str(value), cmds)


def _consume_tokens(value, display):
    """Extrai os caracteres dos tokens (`9`/`A`/`N`/`#`) de `value` seguindo
    `display`, pulando separadores. Caixa preservada (`@U` normaliza depois).
    Literais/derivados de `display` não são emitidos. Usado no strip (`@R`)."""
    s = str(value)
    out = []
    si = 0
    for ch in display:
        if si >= len(s):
            break
        if ch in ('9', 'A', 'N', '#'):
            while si < len(s) and not _tok_match(s[si], ch):
                si += 1
            if si >= len(s):
                break
            out.append(s[si])
            si += 1
    return ''.join(out)


def _fmt_mask_alpha(value, display):
    """Posiciona `value` nos tokens alfanuméricos de `display`, emitindo
    também os literais (exibição)."""
    s = str(value)
    out = []
    si = 0
    for ch in display:
        if si >= len(s):
            break
        if ch in ('9', 'A', 'N', '#'):
            while si < len(s) and not _tok_match(s[si], ch):
                si += 1
            if si >= len(s):
                break
            out.append(s[si])
            si += 1
        else:
            out.append(ch)
    return ''.join(out)


def mask_strip(value, mask):
    """Remove literais/separadores de `value` seguindo `mask`, ficando só com
    os caracteres dos tokens (comando `@R`). Sem corpo (`@R` sozinho) mantém
    só alfanuméricos. None → ''.
    """
    if value is None:
        return ''
    _, display = parse_mask_commands(mask)
    if display:
        return _consume_tokens(value, display).replace('\u00A0', '')
    return re.sub(r'[^A-Za-z0-9]', '', str(value))


def fmt_mask_cmd(value, mask, decimals=None, currency=None):
    """Render de número para lista/readonly com comandos `B`/`X`.

    `B`: '' quando o valor é zero. `X`: sufixo `' C'` (crédito) / `' D'`
    (débito). Moeda/decimais entram na base (money se `currency`, senão
    `fmt_num` com `decimals`). None → ''.
    """
    if value is None:
        return ''
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    cmds, _ = parse_mask_commands(mask)
    if 'B' in cmds and num == 0:
        return ''
    if normalize_currency(currency) is not None:
        base = fmt_money(num, currency)
    else:
        base = fmt_num(num, decimals)
    if 'X' in cmds:
        if num < 0:
            base += ' D'
        elif num > 0:
            base += ' C'
    return base


def _mask_decimals(display):
    """Casas decimais inferidas da máscara: nº de `9` após o último `'./,'`.

    Ex.: '9.999,99' → 2; '999.999' → None (sem decimais claras).
    """
    if not display:
        return None
    idx = max(display.rfind('.'), display.rfind(','))
    if idx < 0:
        return None
    tail = display[idx + 1:]
    if not tail or any(c != '9' for c in tail):
        return None
    return len(tail)


def format(value, mask):
    """Formata QUALQUER valor por uma máscara (espelho JS `format`).

    - data/hora (`date`/`datetime`/`time`) com tokens de data → `fmt_mask`;
    - número (int/float/Decimal) → render numérico: casas inferidas da
      máscara + comandos `B` (branco se zero) / `X` (sufixo C/D);
    - string → `fmt_mask` (tokens `9`/`A`/`N`/`#` + comandos texto U/L/C/T).
    """
    if value is None:
        return ''
    cmds, display = parse_mask_commands(mask)
    if hasattr(value, 'strftime') and has_date_tokens(display):
        return fmt_mask(value, mask)
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return fmt_mask_cmd(value, mask, _mask_decimals(display))
    return fmt_mask(value, mask)


def _fmt_mask_data(value, mask):
    """Formata data/hora pela máscara com tokens (ver `fmt_mask`)."""
    rep = {}
    if hasattr(value, 'year'):
        y, m, d = value.year, value.month, value.day
        rep.update({
            'aaaa': f'{y:04d}',
            'yyyy': f'{y:04d}',
            'aa': f'{y % 100:02d}',
            'yy': f'{y % 100:02d}',
            'mmm': _MES_PT[m - 1],
            'mm': f'{m:02d}',
            'ddd': _DOW_PT[value.weekday()],
            'dd': f'{d:02d}',
        })
    if hasattr(value, 'hour'):
        rep['hh'] = f'{value.hour:02d}'
        rep['ii'] = f'{value.minute:02d}'
        rep['ss'] = f'{value.second:02d}'
        if 'mm' not in rep:
            rep['mm'] = f'{value.minute:02d}'
    if hasattr(value, 'year'):
        digits = f'{value.day:02d}{value.month:02d}{value.year:04d}'
    elif hasattr(value, 'hour'):
        digits = f'{value.hour:02d}{value.minute:02d}{value.second:02d}'
    else:
        digits = ''
    out = []
    di = 0
    for ch in mask:
        if ch == '9':
            if di < len(digits):
                out.append(digits[di])
                di += 1
            else:
                break
        else:
            out.append(ch)
    text = ''.join(out)
    for tok in ('aaaa', 'yyyy', 'aa', 'yy', 'mmm', 'mm', 'ddd', 'dd', 'hh', 'ii', 'ss'):
        if tok in text:
            text = text.replace(tok, rep[tok])
    return text


# ── Parse de máscara de data/hora (lado servidor) ───────────────────────────
_MASK_TOKENS = {
    'aaaa': ('group', 'Y', '\\d{4}'), 'yyyy': ('group', 'Y', '\\d{4}'),
    'aa': ('group', 'y', '\\d{2}'), 'yy': ('group', 'y', '\\d{2}'),
    'mm': ('group', 'm', '\\d{1,2}'),
    'dd': ('group', 'd', '\\d{1,2}'),
    'hh': ('group', 'H', '\\d{1,2}'),
    'ii': ('group', 'M', '\\d{1,2}'),
    'ss': ('group', 'S', '\\d{1,2}'),
}
_MASK_TEXT_TOKENS = {
    'ddd': '[A-Za-záéíóúÁÉÍÓÚãõâêôÂÊÔçÇüÜ.\\-]{2,}',   # dia da semana (derivado)
    'mmm': '[A-Za-záéíóúÁÉÍÓÚãõâêôÂÊÔçÇüÜ.\\-]{2,}',   # mês abreviado (derivado)
}
_MASK_TOKEN_ORDER = ('aaaa', 'yyyy', 'mmm', 'ddd', 'aa', 'yy', 'dd', 'mm', 'hh', 'ii', 'ss', '9')


def _coerce_masked_datetime(value, mask, input_type):
    """Faz parse de `value` formatado por uma máscara com tokens de data/hora,
    inclusive os derivados `ddd`/`mmm` (dia da semana / mês abreviado), que são
    ignorados no parse. Comandos `@X` do prefixo são ignorados. Retorna
    date/time/datetime ou None se não bater."""
    _, display = parse_mask_commands(mask)
    if not display:
        return None

    def _tokens():
        i = 0
        while i < len(display):
            nxt = None
            for tok in _MASK_TOKEN_ORDER:
                if display.startswith(tok, i):
                    nxt = tok
                    break
            if nxt:
                yield nxt
                i += len(nxt)
            else:
                yield display[i]
                i += 1

    def _placeholder(tok):
        if tok == '9':
            return ('group', 'dig', r'\d')
        t = _MASK_TOKENS.get(tok)
        if t is not None:
            kind, key, pat = t
            if tok == 'mm' and input_type == 'time':
                key = 'M'
            return (kind, key, pat)
        if tok in _MASK_TEXT_TOKENS:
            return ('skip', None, _MASK_TEXT_TOKENS[tok])
        return ('lit', None, re.escape(tok))

    parts, fields = [], {}
    for tok in _tokens():
        kind, key, pat = _placeholder(tok)
        if kind == 'skip':
            parts.append(pat)
        elif kind == 'group':
            gname = f'g{len(fields)}'
            fields[gname] = key
            parts.append(f'(?P<{gname}>{pat})')
        else:
            parts.append(pat)
    m = re.fullmatch(''.join(parts), value.strip())
    if not m:
        return None
    try:
        vals = {key: int(m.group(g)) for g, key in fields.items()}
    except (TypeError, ValueError):
        return None
    y = vals.get('Y', vals.get('y', 1))
    if 'Y' not in vals and 'y' in vals:
        y = 2000 + y if y < 69 else 1900 + y
    mo = vals.get('m', 1)
    d = vals.get('d', 1)
    if input_type == 'date':
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    h, mi, s = vals.get('H', 0), vals.get('M', 0), vals.get('S', 0)
    try:
        if input_type == 'time':
            return time(h, mi, s)
        return datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None


# ── Números / moeda ──────────────────────────────────────────────────────────
def parse_brl(value):
    if not value:
        return None
    if ',' in value:
        return float(value.replace('.', '').replace(',', '.'))
    return float(value)


def _fmt_number(value, locale):
    """Número com 2 decimais no agrupamento do locale (sem símbolo)."""
    if value is None:
        return '0,00' if locale == 'pt-BR' else '0.00'
    try:
        num = f'{float(value):,.2f}'
    except (TypeError, ValueError):
        return str(value)
    if locale == 'pt-BR':
        num = num.replace(',', 'X').replace('.', ',').replace('X', '.')
    return num


def normalize_currency(cur):
    """Normaliza a prop `Field.currency` para código de `CURRENCY`.

    `True`/`'brl'` legados e `1` → padrão; `0`/`None`/`False` → desligado
    (None); código desconhecido → desligado (nunca quebra, nunca mente
    símbolo). Retorna o código int ou None.
    """
    if cur is None or cur is False or cur == 0:
        return None
    if cur is True:
        return DEFAULT_CURRENCY
    if isinstance(cur, str):
        if cur.strip().lower() == 'brl':
            return DEFAULT_CURRENCY
        return None
    try:
        code = int(cur)
    except (TypeError, ValueError):
        return None
    return code if CURRENCY.get(code) else None


def currency_symbol(cur):
    """Símbolo da moeda (`'R$'`) a partir do código/legado; '' se desligado."""
    code = normalize_currency(cur)
    info = CURRENCY.get(code) if code is not None else None
    return info['symbol'] if info else ''


def fmt_brl(value):
    """Filtro legado `brl` (sem símbolo; None → '0,00')."""
    if value is None:
        return '0,00'
    return _fmt_number(value, 'pt-BR')


def fmt_money(value, cur=DEFAULT_CURRENCY):
    """Formata valor monetário pelo código de `CURRENCY` (filtro `money`).

    `fmt_money(v)` sem código = padrão (BRL), idêntico ao antigo `fmt_brl`.
    """
    code = normalize_currency(cur)
    if code is None:
        code = DEFAULT_CURRENCY
    info = CURRENCY.get(code) or CURRENCY[DEFAULT_CURRENCY]
    num = _fmt_number(value, info['locale'])
    return f"{info['symbol']} {num}" if info['symbol'] else num


def fmt_percent(value):
    """Formata percentual com 1 decimal e sufixo '%' (ex.: 12.5 → '12,5%')."""
    if value is None:
        return '—'
    return f'{value:,.1f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + '%'


def fmt_num(value, decimals=None):
    """Número pt-BR p/ inputs (filtro `fmt_num`): casas de `decimals`, sem símbolo.

    `None`/'' → ''. Sem `decimals` (ou 0) → inteiro sem agrupar ('1000'), para
    que a leitura de volta seja inequívoca (ponto = decimal só com vírgula).
    Com `decimals` > 0 → agrupa milhar e fixa as casas ('1.234,56').
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return ''
    try:
        dec = int(decimals) if decimals is not None else 0
    except (TypeError, ValueError):
        dec = 0
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if dec <= 0:
        return str(int(num)) if num.is_integer() else str(num)
    return f'{num:,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_id(value):
    if value is None:
        return '0'
    formatted = f'{value:,}'.replace(',', '.')
    return ('%7s' % formatted).replace(' ', '\u00A0')


# ── Data/hora ────────────────────────────────────────────────────────────────
def fmt_zero(value):
    if not value:
        return ''
    return "%.1f" % value


def fmt_zero_int(value):
    if not value:
        return ''
    return "%.0f" % value


def fmt_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def fmt_datetime(value):
    if not value:
        return ''
    try:
        return value.strftime('%d/%m/%Y %H:%M')
    except AttributeError:
        return str(value)


# ── Transforms de texto ──────────────────────────────────────────────────────
def _title_case(text):
    words = text.strip().split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        else:
            result.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(result)


def apply_transform(text, mode):
    """Efeito de texto: 'upper' | 'title' | 'lower' (None/other = intacto)."""
    if not text or not mode:
        return text
    mode = mode.lower()
    if mode == 'upper':
        return str(text).upper()
    if mode == 'lower':
        return str(text).lower()
    if mode == 'title':
        return str(text).title()
    return text


def apply_transform_value(val, transform, field=None):
    """Aplica `transform` a `val` (string). Tolerante a não-string/None."""
    if not val or not isinstance(val, str):
        return val
    if transform == 'upper':
        return val.strip().upper()
    if transform == 'lower':
        return val.strip().lower()
    if transform == 'cap':
        s = val.strip()
        return s[:1].upper() + s[1:] if s else s
    if transform == 'title':
        return _title_case(val.strip())
    if callable(transform):
        return transform(val, field)
    return val


# ── Validadores ──────────────────────────────────────────────────────────────
def validar_cpf(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 11 or s == s[0] * 11:
        return False
    soma = sum(int(s[i]) * (10 - i) for i in range(9))
    d1 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    if d1 != int(s[9]):
        return False
    soma = sum(int(s[i]) * (11 - i) for i in range(10))
    d2 = 0 if (soma * 10) % 11 % 11 == 10 else (soma * 10) % 11
    return d2 == int(s[10])


def validar_cnpj(n):
    s = re.sub(r'\D', '', n)
    if len(s) != 14 or s == s[0] * 14:
        return False
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w1[i] for i in range(12))
    d1 = 0 if soma % 11 < 2 else 11 - soma % 11
    if d1 != int(s[12]):
        return False
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(s[i]) * w2[i] for i in range(13))
    d2 = 0 if soma % 11 < 2 else 11 - soma % 11
    return d2 == int(s[13])


VALIDATORS = {
    'cpf': validar_cpf,
    'cnpj': validar_cnpj,
}


def resolve_validator(validate):
    """Normaliza `Field.validate` numa callable de validação.

    - `str`   → chave em `VALIDATORS` ('cpf'/'cnpj').
    - callable → usada direto.
    - `None`/desconhecido → None (sem validação).
    """
    if callable(validate):
        return validate
    if isinstance(validate, str):
        return VALIDATORS.get(validate)
    if isinstance(validate, (list, tuple)):
        fns = [resolve_validator(v) for v in validate]
        return (lambda v: all(f(v) for f in fns if f)) if any(fns) else None
    return None