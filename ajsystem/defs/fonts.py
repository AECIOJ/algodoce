"""Grade do relatório: CPI × LPI e o catálogo FIXO de fontes.

A grade é uma conta só, em polegada:

    coluna = 25,4 / CPI      linha = 25,4 / LPI
    body   = 60 / LPI  (pt)   stretch = 7200 / (advance × body × CPI) %

`CPI` e `LPI` são o **valor real**, nunca um índice: `CPI(5)` é cinco caracteres
por polegada e não "o quinto degrau". São as duas únicas coisas que decidem a
geometria, e nenhuma delas depende da font.

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

# Letter -> value. `S` de Semi-condensed, que é o termo real de tipografia (e não
# bate com o `I` de italic, que é do outro eixo).
CPI_LETTERS = {'E': 5, 'N': 10, 'S': 17, 'C': 20}
CPI_VALUES = (5, 10, 17, 20)
CPI_DEFAULT = 10

LPI_VALUES = (6, 8)
LPI_DEFAULT = 6

# A tabela escolhe o PRIMEIRO que couber na folha, do mais legível para o mais
# compacto — então a escada vai do maior para o menor CPI. O `E` (5) fica de
# fora de propósito: é estilo de título, não pitch de texto corrido.
TABLE_LADDER = (10, 17, 20)

# Traço do glifo. São as 8 combinações que o fpdf2 sabe desenhar — nem mais nem
# menos. `U` (underline) estava prometido na docstring e recusado no código.
STYLES = ('', 'B', 'I', 'U', 'BI', 'BU', 'IU', 'BIU')

# Style do fpdf2 -> sufixo do arquivo. `BI` é uma face só (BoldItalic), não as
# duas combinadas.
FACE_SUFFIX = {'': 'Regular', 'B': 'Bold', 'I': 'Italic', 'BI': 'BoldItalic'}

INK_MAX = 1.2  # em; ver a conta na docstring do módulo


def cpi(value):
    """Normaliza `CPI`: letter (`E`/`N`/`S`/`C`) ou número. Devolve o valor."""
    if isinstance(value, str):
        _v = value.strip().upper()
        if _v in CPI_LETTERS:
            return CPI_LETTERS[_v]
        try:
            value = int(_v)
        except ValueError:
            raise ValueError(
                f"CPI: {value!r} não é letra ({'|'.join(CPI_LETTERS)}) nem número") from None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"CPI: {value!r} não é número")
    if int(value) != value or value not in CPI_VALUES:
        raise ValueError(
            f"CPI: {value:g} fora de {list(CPI_VALUES)} (ou letra: {sorted(CPI_LETTERS)})")
    return int(value)


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


def col_mm(value):
    """Largura da coluna em mm."""
    return 25.4 / cpi(value)


def line_mm(value):
    """Altura da linha em mm."""
    return 25.4 / lpi(value)


def body_pt(value):
    """Corpo da fonte em pt, derivado do LPI (60/LPI): 6 -> 10pt, 8 -> 7.5pt."""
    return 60.0 / lpi(value)


def stretch_pct(advance, body, value):
    """`Tz` que faz o glifo ocupar exatamente `25,4/CPI` mm.

    `body` é o corpo em PT já vindo de `body_pt(lpi)` — quem chama é que sabe
    o LPI vigente, e normalizar aqui denovo misturaria os dois eixos.
    """
    return 7200.0 / (advance * body * cpi(value))


def cpi_letter(value):
    """Letra de um CPI, ou o número quando não há nome."""
    _v = cpi(value)
    for _k, _n in CPI_LETTERS.items():
        if _n == _v:
            return _k
    return str(_v)


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