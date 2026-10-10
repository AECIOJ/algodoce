"""Grade do relatório: CPI × LPI e o catálogo FIXO de fontes.

A grade é uma conta só, em polegada:

    coluna = 25,4 / CPI      linha = 25,4 / LPI
    body   = 60 / LPI  (pt)   stretch = 7200 / (advance × body × CPI) %

`CPI` e `LPI` são **o valor real**, nunca um índice. São as duas únicas coisas que
decidem a geometria, e nenhuma delas depende da font.

O `CPI` tem só **três** valores — os modos base da matriz de impressora (10 Pica,
12 Elite, 15 Micron). Todo o resto é **modificador** (`flags`): `E` expandido e
`C` condensado, e o motor resolve a combinação. O autor conhece três números;
`CPI(5)` nem existe, porque se escreve `CPI(10, 'E')`.

**O glifo é esticado para preencher a célula.** O `advance` da font (a largura
do glifo em `em`) só entra na conta do stretch, que é a correção exata de
`25,4/CPI`; por isso trocar a font não move nada — só muda a letra desenhada.
O `set_stretching` do fpdf2 (operador `Tz`) faz isso no PDF, e o
`get_string_width` já conta o stretch, então `align='C'` centraliza certo
desde que o stretch seja aplicado ANTES de medir.

**Condensed e expanded são as duas pontas do mesmo eixo** (`CPI` 5 e 20), não
dois estilos: pedir os dois ao mesmo tempo é pedir 0,5× e 2×, e o produto é 1× —
o normal. O que combina com tudo é o outro eixo, `style` (bold/italic/
underline), que muda o TRAÇO e não a grade.

**A lista de fonts é fixa e os arquivos acompanham o framework** (`defs/fonts/`,
com a licença de cada uma ao lado, como a OFL exige). Não há registro por
caminho: a font precisa estar aqui para a conta valer. Só entra font
MONOSPACED — é o que garante "1 coluna = 1 caractere"; font proporcional
passaria a exigir a largura do glifo mais largo no lugar do advance, que é outra
conta. As métricas (`advance`, `ink`) são lidas do próprio arquivo, então a font
é a fonte da verdade e não uma tabela que pode divergir dela.

`ink` é a altura real dos glifos (desenho, não `OS/2`): o `OS/2` da JetBrains
Mono diz 1,32 em e rejeitaria a font, quando o desenho de verdade para em
0,957 em e cabe na linha com folga. O limite é 1,2 em, que decorre de
`body = 60/LPI` contra `line = 25,4/LPI`.
"""
from pathlib import Path

# --- grade -------------------------------------------------------------------

# Só os três MODOS BASE, como na matriz de impressora: Pica, Elite e Micron.
# Todo valor fora daqui é DERIVADO e se escreve com `flags` — `CPI(10, 'E')` em
# vez de `CPI(5)`. O autor conhece três números; o motor resolve os outros.
CPI_VALUES = (10, 12, 15)
CPI_DEFAULT = 10

# O pitch condensado de cada base. `15` está fora DE PROPÓSITO: é a única célula
# da matriz que a impressora recusa ('Não aceita'), e `cpi_final` devolve o
# próprio base quando o modo pede condensado a partir daqui.
CPI_CONDENSED = {10: 17.1, 12: 20}

# Modificadores: `N` normal (ou vazio), `E` expandido, `C` condensado. A ordem
# não importa — `'EC'` e `'CE'` são o mesmo pedido.
FLAGS = 'NEC'

LPI_VALUES = (6, 8)
LPI_DEFAULT = 6

# A tabela escolhe o PRIMEIRO que couber na folha, do mais legível para o mais
# compacto. Entra a escada inteira, inclusive os dois condensados: a densidade da
# tabela é escolha do motor, então o autor nunca escreve esses números.
TABLE_LADDER = (10, 12, 15, 17.1, 20)

# Traço do glifo. São as 8 combinações que o fpdf2 sabe desenhar — nem mais nem
# menos. `U` (underline) estava prometido na docstring e recusado no código.
STYLES = ('', 'B', 'I', 'U', 'BI', 'BU', 'IU', 'BIU')

# Style do fpdf2 -> sufixo do arquivo. `BI` é uma face só (BoldItalic), não as
# duas combinadas.
FACE_SUFFIX = {'': 'Regular', 'B': 'Bold', 'I': 'Italic', 'BI': 'BoldItalic'}

INK_MAX = 1.2  # em; ver a conta na docstring do módulo


def cpi(value):
    """Normaliza o BASE do `CPI`: só 10, 12 ou 15. Devolve o valor.

    O erro aqui é o mais instrutivo do módulo, porque todo valor derivado
    continua alcançável por letra: `CPI(5)` diz para escrever `CPI(10, 'E')`.
    """
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            raise ValueError(
                f"CPI: {value!r} não é número; use um de {list(CPI_VALUES)}"
            ) from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"CPI: {value!r} não é número")
    if value not in CPI_VALUES:
        raise ValueError(
            f"CPI: {value:g} não é um base; use um de {list(CPI_VALUES)}"
            + _sugere(value))
    return int(value)


def _sugere(value):
    """Se o número é um valor DERIVADO, diz com qual base e flag se escreve."""
    _v = float(value)
    for _b in CPI_VALUES:
        if abs(_v - _b / 2) < 1e-9:
            return f" (use CPI({_b}, 'E'))"
        if _b in CPI_CONDENSED:
            if abs(_v - CPI_CONDENSED[_b]) < 1e-9:
                return f" (use CPI({_b}, 'C'))"
            if abs(_v - CPI_CONDENSED[_b] / 2) < 1e-9:
                return f" (use CPI({_b}, 'EC'))"
    return ''


def flags(value):
    """Normaliza `flags`: '' | 'N' | 'E' | 'C' | 'EC'. Devolve em caixa alta.

    `N` é o "sem modificador" explícito e por isso **não** combina com `E`/`C`:
    `'NE'` é pedir normal e expandido ao mesmo tempo, e deixar passar seria uma
    letra ignorada em silêncio.
    """
    if value is None:
        return ''
    if not isinstance(value, str):
        raise ValueError(f"flags: {value!r} não é str de letras ({FLAGS})")
    _f = value.strip().upper()
    if not _f or _f == 'N':
        return ''
    _bad = [c for c in _f if c not in 'EC']
    if _bad or len(set(_f)) != len(_f):
        raise ValueError(
            f"flags: {value!r} inválido — use 'N', 'E', 'C' ou 'EC' "
            f"(na ordem que quiser), sem repetir letra")
    # ordem canônica, para que 'CE' e 'EC' virem a mesma string
    return ''.join(c for c in 'EC' if c in _f)


def cpi_final(base, fl=''):
    """(base, flags) -> o CPI final. A matriz inteira sai daqui.

        expandido        = base / 2            (exato nos três)
        condensado       = CPI_CONDENSED[base] ('15' não tem: fica no base)
        condensado+expand = condensado / 2

    Onde a matriz recusa, devolve o próprio base — é o comportamento pedido, e
    não é calado para o caso que a matriz aceita.
    """
    _b = cpi(base)
    _f = flags(fl)
    _e, _c = 'E' in _f, 'C' in _f
    if _c:
        _cond = CPI_CONDENSED.get(_b)
        if _cond is None:      # Micron não aceita condensado
            return _b
        return _cond / 2 if _e else _cond
    return _b / 2 if _e else _b


def lpi(value):
    """Normaliza `LPI`: linhas por polegada. Devolve o valor."""
    if isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise ValueError(f"LPI: {value!r} não é número") from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"LPI: {value!r} não é número")
    if int(value) != value or value not in LPI_VALUES:
        raise ValueError(f"LPI: {value:g} fora de {list(LPI_VALUES)}")
    return int(value)


def cpi_geom(value):
    """CPI como número, para MEDIR — aceita base, expandido e condensado.

    `cpi` é a porta do que se DECLARA e só deixa passar os bases; medir é outra
    conta. A escada da tabela (`TABLE_LADDER`) anda por 17.1 e 20, que são
    valores derivados, e `col_mm` era `cpi()` por dentro: na 4ªTIla da escada
    estourava `ValueError` no lugar do recado de "não cabe".
    """
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError:
            raise ValueError(
                f"CPI: {value!r} não é número; use um de {list(CPI_VALUES)}"
            ) from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"CPI: {value!r} não é número")
    if value in CPI_VALUES:
        return int(value)
    for base, cond in CPI_CONDENSED.items():
        if abs(value - cond) < 1e-9 or abs(value - cond / 2) < 1e-9:
            return value
    for base in CPI_VALUES:
        if abs(value - base / 2) < 1e-9:
            return value
    raise ValueError(
        f"CPI: {value:g} fora da grade; use um de {list(CPI_VALUES)}"
        + _sugere(value))


def col_mm(value):
    """Largura da coluna em mm."""
    return 25.4 / cpi_geom(value)


def line_mm(value):
    """Altura da linha em mm."""
    return 25.4 / lpi(value)


def body_pt(value):
    """Corpo da fonte em pt, derivado do LPI (60/LPI): 6 -> 10pt, 8 -> 7.5pt."""
    return 60.0 / lpi(value)


def stretch_pct(advance, body, value):
    """`Tz` que faz o glifo ocupar exatamente `25,4/CPI` mm.

    `value` aqui é o CPI **FINAL** (o que `cpi_final` já resolveu), não um base:
    normalizar de novo pegaria o valor derivado — 5, 7,5, 20 — e recusaria, que é
    justamente o que a matriz existe para alcançar.

    `body` é o corpo em PT já vindo de `body_pt(lpi)` — quem chama é que sabe o
    LPI vigente, e normalizar aqui misturaria os dois eixos.
    """
    return 7200.0 / (advance * body * float(value))


# --- catálogo de fonts -------------------------------------------------------

_FONTS_DIR = Path(__file__).resolve().parent / 'fonts'

# `prefix` monta os 4 arquivos: `<prefix>Regular.ttf`, `<prefix>Italic.ttf`,
# `<prefix>Bold.ttf`, `<prefix>BoldItalic.ttf`.
FONTS = {
    'courier': {'prefix': None, 'core': 'courier', 'advance': 0.6000, 'ink': 0.7860},
    'jetbrains': {'prefix': 'JetBrainsMonoNL-', 'folder': 'jetbrains'},
    'hack': {'prefix': 'Hack-', 'folder': 'hack'},
    'space': {'prefix': 'SpaceMono-', 'folder': 'space'},
    'plex': {'prefix': 'IBMPlexMono-', 'folder': 'plex'},
}

_CACHE = {}


def _measure(path):
    """(advance, ink) do arquivo: advance pelo `hmtx`, ink pelo desenho real.

    O ink vem dos limites dos glifos, e não do `OS/2` — o `OS/2` é métrica
    tipográfica, folgada para caber acento e outra escrita, e reprova fonts que
    cabem folgadas. O advance vem do `hmtx` de `i`, `W`, `M` e `0`: se diferirem,
    a font não é monospaced e a conta não vale.
    """
    from fontTools.ttLib import TTFont
    from fontTools.pens.boundsPen import BoundsPen
    tt = TTFont(str(path), fontNumber=0, lazy=True)
    try:
        upem = tt['head'].unitsPerEm
        cmap = tt.getBestCmap()
        sample = [cmap.get(ord(c)) for c in 'iWM0']
        if any(g is None for g in sample):
            raise ValueError('fonte sem os glifos básicos i/W/M/0')
        advances = {tt['hmtx'][g][0] for g in sample}
        if len(advances) != 1:
            raise ValueError(
                'fonte NÃO é monospaced (advance difere entre i/W/M/0) — '
                'a grade exige 1 coluna = 1 caractere')
        glyphs = tt.getGlyphSet()
        ymin = ymax = 0.0
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789gjpqy':
            glyph = cmap.get(ord(c))
            if glyph is None:
                continue
            bp = BoundsPen(glyphs)
            glyphs[glyph].draw(bp)
            if bp.bounds:
                ymin = min(ymin, bp.bounds[1])
                ymax = max(ymax, bp.bounds[3])
        return advances.pop() / upem, (ymax - ymin) / upem
    finally:
        tt.close()


def font(name):
    """Resolve o nome no catálogo -> `{name, family, core, advance, ink, faces}`.

    `faces` mapeia o style do fpdf2 (`''`/`B`/`I`/`BI`) para o caminho do
    arquivo. O `courier` não tem arquivo: é fonte de núcleo do PDF, resolvida
    pelo leitor, e por isso o body/style saem sem registro.
    """
    if name in _CACHE:
        return _CACHE[name]
    spec = FONTS.get(name)
    if spec is None:
        raise ValueError(
            f"font {name!r} não está no catálogo; use uma de {sorted(FONTS)}")
    if spec.get('core'):
        info = {'name': name, 'core': spec['core'], 'family': name,
                'advance': spec['advance'], 'ink': spec['ink'], 'faces': {}}
    else:
        folder = _FONTS_DIR / spec['folder']
        faces = {}
        for style, suffix in FACE_SUFFIX.items():
            path = folder / (spec['prefix'] + suffix + '.ttf')
            if not path.is_file():
                raise FileNotFoundError(
                    f"font {name!r}: falta {path.name} em {folder} — "
                    f"sem a face {style!r} o style correspondente levanta no render")
            faces[style] = path
        advance, ink = _measure(faces[''])
        if ink > INK_MAX:
            raise ValueError(
                f"font {name!r}: ink {ink:.4f} em passa do limite {INK_MAX} "
                f"— não cabe na linha em nenhum LPI")
        info = {'name': name, 'core': None, 'family': name,
                'advance': advance, 'ink': ink, 'faces': faces}
    _CACHE[name] = info
    return info


def register(pdf, name):
    """Registra as 4 faces da família no `pdf` (idempotente).

    O `add_font` é por (família, style), e `set_font` escolhe a face pelo
    style — é o que faz o bold e o italic saírem com o desenho de verdade em vez
    de sintético do leitor. Sem a face registrada, `set_font('x','I')` levanta
    `Undefined font` do fpdf2, que é exceção de outra biblioteca no meio do
    relatório.
    """
    info = font(name)
    if info['core']:
        return info
    # O subsetter do fontTools avisa em WARNING e descarta a tabela `TTFA`
    # (metadado do FontLab que o Hack carrega) — 4 linhas por PDF de ruído sobre
    # algo que o autor do report não pediu. Silencia só durante o registro, só
    # esse logger, e volta ao normal na saída.
    import logging
    _log = logging.getLogger('fontTools.subset')
    _antes = _log.level
    _log.setLevel(logging.ERROR)
    try:
        for style, path in info['faces'].items():
            # fpdf2 indexa `pdf.fonts` por `nome + style` (ex.: 'hackBI') — a
            # checagem tem de usar a MESMA chave, senão o `add_font` repetido
            # dispara `UserWarning: font already added` a cada desenho.
            if name + style not in pdf.fonts:
                pdf.add_font(name, style, str(path))
    finally:
        _log.setLevel(_antes)
    return info