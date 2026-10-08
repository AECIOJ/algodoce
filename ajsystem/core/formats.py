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

from ajsystem.defs.constants import CONNECTORS

# ── Estado de formatação (default en-US; o host sobrescreve via masks) ────────
DECIMAL = '.'
THOUSAND = ','
MONEY = {'USD': '$'}
DEFAULT_MONEY = 'USD'


def definir_formatacao(decimal=None, thousand=None, money=None, default_money=None):
    """Publica separadores/moedas do app (chamado por `defs/masks.definir_masks`)."""
    global DECIMAL, THOUSAND, MONEY, DEFAULT_MONEY
    if decimal is not None:
        DECIMAL = decimal
    if thousand is not None:
        THOUSAND = thousand
    if money is not None:
        MONEY = dict(money)
    if default_money is not None:
        DEFAULT_MONEY = default_money


__all__ = [
    # mask display + tokens
    'has_date_tokens', 'fmt_mask', '_fmt_mask_data',
    'parse_mask', 'parse_mask_commands', 'mask_money_id', 'mask_strip', 'fmt_mask_cmd', 'format',
    '_DOW_PT', '_MES_PT', '_DATE_TOKENS_RE',
    # formatação (separadores/moedas do app)
    'definir_formatacao', 'DECIMAL', 'THOUSAND', 'MONEY', 'DEFAULT_MONEY',
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
# `M` = money: `@M(id) 999,999.99` (id ISO do catálogo `MONEY`; sem id = default).
_MASK_COMMANDS = {
    'U': 'upper', 'L': 'lower', 'C': 'cap', 'T': 'title',
    'R': 'R', 'B': 'B', 'X': 'X', 'M': 'M',
}
_TEXT_COMMANDS = ('U', 'L', 'C', 'T')


def parse_mask(mask):
    """Separa `(cmds, display, money_id)`. Comandos `@X` são prefixo contíguo;
    `@M(id)` consome o id entre parênteses (id de `MONEY`).

    Ex.: '@M(BRL) 999,999.99' → ({'M'}, '999,999.99', 'BRL').
    Fail-fast: comando desconhecido / `)` ausente / `@` no corpo.
    """
    if not mask:
        return frozenset(), '', None
    s = str(mask).strip()
    cmds = []
    money = None
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
        if 'M' in letters and i < len(s) and s[i] == '(':
            k = s.find(')', i + 1)
            if k < 0:
                raise ValueError(f"MASK: ')' ausente no money de '{mask}'")
            money = s[i + 1:k].strip() or None
            i = k + 1
        if i < len(s) and s[i] == '@':
            continue
        break
    display = s[i:].lstrip(' \t')
    if display.startswith('@'):
        raise ValueError(f"MASK: comandos devem ser contíguos em '{mask}'")
    return frozenset(cmds), display, money


def parse_mask_commands(mask):
    """Backward-compat: `(cmds, display)` de `parse_mask` (descarta o money id).

    Ex.: '@BX 999,999.99' → (frozenset({'B', 'X'}), '999,999.99').
    """
    cmds, display, _ = parse_mask(mask)
    return cmds, display


def mask_money_id(mask):
    """Id de moeda da máscara: `@M(id)` (validado em `MONEY`) ou, `@M` sem id,
    `DEFAULT_MONEY`; `None` se a máscara não tem `@M`. Uso interno do motor —
    `Field.currency` é derivada daqui (a mask é a fonte da moeda)."""
    if not mask:
        return None
    cmds, _, mid = parse_mask(mask)
    if mid:
        return mid if mid in MONEY else None
    return DEFAULT_MONEY if 'M' in cmds else None


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


def _group_digits(digits, sep):
    """Agrupa `digits` (str) de 3 em 3 da direita, preservando zeros à esquerda."""
    out = []
    while len(digits) > 3:
        out.insert(0, digits[-3:])
        digits = digits[:-3]
    out.insert(0, digits)
    return sep.join(out)


def _num_mask_spec(display):
    """(decimals, group, pad_int, width_int) da máscara numérica canônica.

    `0`=dígito com pad; `9`=opcional; `,`=milhar (agrupa); `.`=decimal."""
    body = display or ''
    int_part, _, dec_part = body.partition('.')
    int_digits = int_part.replace(',', '')
    decimals = sum(1 for c in dec_part if c in '09')
    group = ',' in body
    pad_int = '0' in int_digits
    width_int = sum(1 for c in int_digits if c in '09')
    return decimals, group, pad_int, width_int


def _is_num_mask(display):
    """Máscara canônica numérica: só `0`/`9`/`,`/`.` (milhar/decimal). Máscaras
    de texto/documento (CPF `999.999.999-99`, tel `(99) 99999-9999`, placa
    `AAA-9A99`) têm literais (`-`/`(`/`)`/letras) → não são numéricas; quem as
    renderiza é o caminho de texto (`fmt_mask`)."""
    return bool(display) and all(c in '09,.' for c in display)


def _render_num_mask(value, display):
    """Número pela máscara canônica, com `THOUSAND`/`DECIMAL` de saída."""
    decimals, group, pad_int, width_int = _num_mask_spec(display)
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f'{abs(num):.{decimals}f}'
    int_s, _, frac_s = s.partition('.')
    if pad_int and width_int:
        int_s = int_s.rjust(width_int, '0')
    if group:
        int_s = _group_digits(int_s, THOUSAND)
    out = int_s + (DECIMAL + frac_s if decimals else '')
    return ('-' + out) if num < 0 else out


def _fmt_dec(value, decimals=2, group=True):
    """Número com `decimals` casas nos separadores do app (base sem máscara)."""
    if value is None:
        value = 0
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f'{abs(num):,.{decimals}f}' if group else f'{abs(num):.{decimals}f}'
    if group:
        s = (s.replace(',', '\x00').replace('.', '\x01')
              .replace('\x00', THOUSAND).replace('\x01', DECIMAL))
    else:
        s = s.replace('.', DECIMAL)
    return ('-' + s) if num < 0 else s


def fmt_mask_cmd(value, mask, decimals=None, currency=None):
    """Render numérico para lista/readonly (máscara canônica + moeda/comandos).

    `@M(id)` (a fonte da moeda) ou `currency` (id derivado pelo motor de
    `Field.currency`) → símbolo de `MONEY`; `B` = '' quando zero;
    `X` = sufixo ' C'/' D'. Sem corpo e sem `M`: número com `decimals` (grupo).
    """
    if value is None:
        return ''
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    cmds, display, money = parse_mask(mask) if mask else (frozenset(), '', None)
    if display and not _is_num_mask(display):
        return fmt_mask(value, mask)
    if 'B' in cmds and num == 0:
        return ''
    mid = money or normalize_currency(currency)
    if 'M' in cmds and mid is None:
        mid = DEFAULT_MONEY
    dec = decimals if decimals is not None else (_mask_decimals(display) or 2)
    if mid is not None:
        sym = MONEY.get(mid, '')
        body = _render_num_mask(num, display) if display else _fmt_dec(num, dec)
        base = f'{sym} {body}' if sym else body
    elif display:
        base = _render_num_mask(num, display)
    else:
        base = _fmt_dec(num, dec)
    if 'X' in cmds:
        base += ' D' if num < 0 else (' C' if num > 0 else '')
    return base


def _mask_decimals(display):
    """Casas decimais da máscara canônica: `0`/`9` após o último `.`."""
    if not display or '.' not in display:
        return None
    dec_part = display.rsplit('.', 1)[1]
    if not dec_part or any(c not in '09' for c in dec_part):
        return None
    return len(dec_part)


def format(value, mask):
    """Formata QUALQUER valor por uma máscara (espelho JS `format`).

    - data/hora com tokens de data → `fmt_mask`;
    - número com máscara canônica numérica (ou sem máscara) → `fmt_mask_cmd`
      (`@M(id)`, separadores do app);
    - string ou número em máscara de texto/documento → `fmt_mask`
      (CPF `999.999.999-99` com `9` = dígito, literais preservados).
    """
    if value is None:
        return ''
    _, display, _ = parse_mask(mask)
    if hasattr(value, 'strftime') and has_date_tokens(display):
        return fmt_mask(value, mask)
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool) \
            and (not display or _is_num_mask(display)):
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
    """Texto monetário/numérico → float. Devolve None quando não há número.

    Aceita o que o formulário realmente envia: símbolo de moeda
    ('R$ 29,70'), milhar pt-BR ('1.234,56'), espaço/NBSP como separador,
    o sufixo D/C de débito/crédito e número já pronto (int/float/Decimal).
    Sem vírgula o ponto é decimal ('1.5'); com vírgula, ponto é milhar.
    Espelha o `parseNum` de `static/js/formats.js`.
    """
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    s = str(value).strip().replace('\u00A0', ' ')
    s = re.sub(r'\s+[CD]\s*$', '', s)   # '1.234,56 D'
    s = re.sub(r'[^0-9,.+-]', '', s)     # 'R$ ', '$', '€', 'US$'
    # Vírgula presente = o decimal é o do app e o ponto é milhar ('1.234,56');
    # sem vírgula o ponto é decimal ('6.00', '1.5'). Mesma regra de `as_num`
    # (core/utils.py) e de `_coerce` (core/form.py): um input numérico sem
    # `decimals` guarda o valor canônico, e ler '6.00' como milhar daria 600.
    if DECIMAL in s:
        if THOUSAND and THOUSAND != DECIMAL:
            s = s.replace(THOUSAND, '')
        s = s.replace(DECIMAL, '.')
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _fmt_number(value, locale=None):
    """Número com 2 decimais nos separadores do app (sem símbolo)."""
    return _fmt_dec(value, 2, True)


def normalize_currency(cur):
    """Normaliza uma moeda para id de `MONEY`.

    A fonte é `Field.currency` (derivada pelo motor da `mask` `@M(id)`, já id
    ISO) — mas segue aceitando os legados `True`/`'brl'`/`1` → `DEFAULT_MONEY`;
    `2`→'USD' / `3`→'EUR' (se existirem); `0`/`None`/`False` → desligado (None);
    id ISO de `MONEY` → ele. Nunca mente símbolo: desconhecido → None.
    """
    if cur is None or cur is False or cur == 0:
        return None
    if cur is True:
        return DEFAULT_MONEY
    if isinstance(cur, str):
        s = cur.strip()
        if s.lower() in ('brl', 'real'):
            return DEFAULT_MONEY
        return s if s in MONEY else None
    if isinstance(cur, int) and not isinstance(cur, bool):
        if cur == 1:
            return DEFAULT_MONEY
        legacy = {2: 'USD', 3: 'EUR'}.get(cur)
        return legacy if legacy in MONEY else None
    return None


def currency_symbol(cur):
    """Símbolo da moeda (`'R$'`) a partir do id/legado; '' se desligado."""
    mid = normalize_currency(cur)
    return MONEY.get(mid, '') if mid else ''


def fmt_brl(value):
    """Filtro legado `brl` (sem símbolo; None → '0,00')."""
    return _fmt_dec(value, 2, True)


def fmt_money(value, cur=None):
    """Formata valor monetário pelo id de `MONEY` (filtro `money`).

    `fmt_money(v)` sem id = `DEFAULT_MONEY`.
    """
    mid = normalize_currency(cur) if cur is not None else DEFAULT_MONEY
    if mid is None:
        mid = DEFAULT_MONEY
    sym = MONEY.get(mid, '')
    num = _fmt_dec(value, 2, True)
    return f'{sym} {num}' if sym else num


def fmt_percent(value):
    """Formata percentual com 1 decimal e sufixo '%' (ex.: 12.5 → '12,5%')."""
    if value is None:
        return '—'
    return _fmt_dec(value, 1, True) + '%'


def num_mask(decimals):
    """Máscara numérica default (canônica) a partir de `decimals`.

    Com milhar: `0` → `'9,999'`; `2` → `'9,999.99'`. O motor troca pelos
    `THOUSAND`/`DECIMAL` do app na renderização.
    """
    d = int(decimals or 0)
    return '9,999' if d <= 0 else f'9,999.{"9" * d}'


def fmt_num(value, decimals=None, group=False):
    """Número p/ inputs (filtro `fmt_num`): casas de `decimals`, sem símbolo.

    `None`/'' → ''. Sem `decimals` (ou 0) → sem agrupar ('1000', '1234,5'),
    para que a leitura de volta seja inequívoca: vírgula presente é o decimal
    do app (e o ponto, milhar); sem vírgula, o ponto é casa decimal.
    Com `decimals` > 0 → agrupa milhar e fixa as casas. `group=True` força o
    separador também sem decimais (exibição). Separadores do app.
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
        if group:
            return _fmt_dec(num, 0, True)
        if num.is_integer():
            return str(int(num))
        # Fração sem casa declarada: sem agrupar (leitura de volta
        # inequívoca) e com o decimal do app — `str(6.5)` vazaria o ponto
        # canônico e o `parseNum` do motor leria '6.5' como 65.
        return str(num).replace('.', DECIMAL)
    return _fmt_dec(num, dec, True)


def fmt_id(value):
    if value is None:
        return '0'
    return ('%7s' % _group_digits(str(value), THOUSAND)).replace(' ', '\u00A0')


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
        if i > 0 and w.lower() in CONNECTORS:
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