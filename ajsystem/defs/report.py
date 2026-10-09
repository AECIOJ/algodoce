"""Configuração declarativa de relatórios PDF (genérico do framework).

Cada sistema declara relatórios via:

    REP = Report(label='...', header={...}, body={...})

E o motor `ajsystem.core.pdf.gerar_pdf_relatorio(report, ...)` os renderiza.
"""
from dataclasses import dataclass, field as dc_field
from typing import Optional, Callable, Union

# Import único nos relatórios do app: `from ajsystem.defs.report import *`
# entrega SÓ os aliases de declaração; o resto (Report*, parse_*, contrato
# DOM) é import explícito, como o motor já faz.
__all__ = [
    'LOGO', 'TITLE', 'TITLES', 'TEXT', 'TABS', 'IND', 'FIELD', 'TEXTS', 'MEMO',
    'CR', 'LF', 'FF', 'FIELDS', 'FONT', 'POS',
    'LINE', 'BOX', 'CIRCLE', 'IMAGE',
    'PCOL', 'PROW', 'LTB', 'RTB', 'NCOL',
]

# A pergunta "isto nomeia um field?" é da máquina genérica; as factories de
# declaração só nisso aplicam a sua política de aceitação.
from ajsystem.core.resolve import field_spec_item  # noqa: E402


# ── Contrato de DOM do container de relatório ──
# O relatório não é só o PDF: ele é injetado num container exclusivo da página,
# que o JS alterna com a página corrente (`reportRender` abre, `closeReport`
# volta sem recarregar). O nome desse container é contrato de três lados:
#   Python  — `Button.into` e `Button.target_into` (ver defs/buttons.py)
#   HTML    — o atributo `id=` em `pages/sys.html`
#   JS      — `getElementById` em `sys.html` e `components/print_overlay.html`
#
# Por isso existem duas formas, e uma é derivada da outra: a crua (`report-content`)
# para o `id=` e o `getElementById`, e a de seletor (`#report-content`) para o
# `Button.into` e o `injectHTML`. Se fossem dois literais soltos, trocar o id
# deixaria um dos lados para trás e o botão renderizaria o HTML sem o JS
# reconhecer o destino — o relatório aparece, a página não some, e o console
# não reclama.
#
# `init.py` expõe as duas como globals Jinja, então os templates leem daqui em
# vez de repetir o literal.
REPORT_ID = 'report-content'
REPORT_CONTENT = f'#{REPORT_ID}'

# Template da página standalone (antes: prop print_template do Report).
PRINT_TEMPLATE = 'components/print_default.html'
# Logo fallback quando o APP não declara (APP.logo = relativo ao static).
LOGO_FALLBACK = 'static/icons/Logo.png'


class _CursorExpr:
    """Expressão de cursor p/ TABS (só PCOL/PROW ± número). Avaliada no motor."""

    __slots__ = ('base', 'offset')

    def __init__(self, base, offset=0):
        self.base = base
        self.offset = offset

    def __add__(self, n):
        if isinstance(n, bool) or not isinstance(n, (int, float)):
            raise TypeError(f"cursor '{self.base}' só soma número")
        return _CursorExpr(self.base, self.offset + n)

    def __sub__(self, n):
        if isinstance(n, bool) or not isinstance(n, (int, float)):
            raise TypeError(f"cursor '{self.base}' só subtrai número")
        return _CursorExpr(self.base, self.offset - n)

    def __repr__(self):
        if not self.offset:
            return self.base
        sign = '+' if self.offset > 0 else '-'
        return f"{self.base}{sign}{abs(self.offset)}"


# Posição corrente do cursor em grade, p/ TABS (forma constante; a string
# 'PCOL+20' segue válida). Importe no relatório: from ajsystem.defs.report import PCOL
PCOL = _CursorExpr('PCOL')
PROW = _CursorExpr('PROW')
# Bordas da última tabela impressa (fallback = área útil) e total de cols.
# LTB/RTB/NCOL valem em âncora, TABS e POS, como PCOL/PROW.
LTB = _CursorExpr('LTB')
RTB = _CursorExpr('RTB')
NCOL = _CursorExpr('NCOL')


@dataclass
class ReportField:
    """Campo para cabeçalho do relatório (dict-only)."""
    field: Optional[str] = None
    label: Optional[str] = None
    align: str = 'left'
    format: Optional[str] = None
    function: Optional[Callable] = None

    def __post_init__(self):
        if self.label is None and self.field:
            self.label = self.field


def parse_header_field(item) -> ReportField:
    """Converte dict -> ReportField."""
    if isinstance(item, dict):
        return ReportField(**item)
    raise TypeError(f"header_field deve ser dict, recebeu {type(item).__name__}: {item!r}")


ITEM_KINDS = ('FIELD', 'TEXT', 'IMAGE', 'LINE', 'BOX', 'CIRCLE', 'LOGO', 'TITLE',
              'TABS', 'POS', 'FIELDS', 'FONT', 'IND', 'TEXTS', 'CR', 'LF', 'FF',
              'MEMO', 'TITLES')


@dataclass
class ReportItem:
    """Item de header/body (forma lista). Sem type = FIELD; MAIÚSCULA = elemento.

    Grafias: 'nome' | {'total': {...}} (FIELD) | {'TEXT': {...}} | 'LOGO' |
    {'LOGO': {...}} | 'TITLE' (1º = título, demais = subtítulo em cascata).
    """
    kind: str = 'FIELD'
    name: str = ''
    config: dict = dc_field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in ITEM_KINDS:
            raise ValueError(f"item '{self.kind}' desconhecido {list(ITEM_KINDS)}")


def _check_props(kind, props, label):
    if not isinstance(props, dict):
        raise ValueError(f"report '{label}': props de '{kind}' devem ser dict")
    return props


def LOGO(anchor=None, lines=None):
    """Factory pura: LOGO() == 'LOGO' (defaults); LOGO('C', 4) explícito."""
    if anchor is None and lines is None:
        return {'LOGO': {}}
    if anchor not in ('C', 'L', 'R'):
        raise ValueError(f"LOGO: âncora '{anchor}' deve ser C|L|R")
    if isinstance(lines, bool) or not isinstance(lines, (int, float)) or lines <= 0:
        raise ValueError(f"LOGO: linhas deve ser número > 0")
    return {'LOGO': {'location': [anchor, lines]}}


def TITLE(text=None, props=None):
    """Factory pura: TITLE() == 'TITLE' (defaults); TITLE('...', {...}) explícito."""
    if text is None and not props:
        return {'TITLE': {}}
    if not ((isinstance(text, str) and text) or callable(text)):
        raise ValueError("TITLE: texto deve ser str não vazia ou callable")
    return {'TITLE': {'text': text, **_check_props('TITLE', props or {}, '')}}


def TITLES(*items):
    """Factory pura: TITLES(['a', ('b', {props})]) = vários TITLE numa tacada.

    Como `TEXTS`/`FIELDS`: item = 'texto' | ('texto', {props}) |
    {'TITLE': {...}}. O texto pode ser callable (o COMPRA deriva o título do
    documento), e quem não passar texto usa o rótulo do report.

    A **cascata é posicional e o `when` vem ANTES dela**: um subtítulo pulado
    não vira título grande. 1º desenhado = `title_font_size`/`title_font_style`,
    os demais = `subtitle_font_size`. Declarar `font_size`/`font_style` na
    entrada muda a fonte **sem** mudar a posição — quem escreve `'A', ('B', ...)`
    continua vendo B como subtítulo, com respiro de subtítulo.
    """
    if len(items) == 1 and isinstance(items[0], (list, tuple)):
        items = tuple(items[0])
    out = []
    for it in items:
        if isinstance(it, str):
            out.append({'TITLE': {'text': it}})
        elif callable(it):
            out.append({'TITLE': {'text': it}})
        elif isinstance(it, tuple) and len(it) == 2 and isinstance(it[1], dict):
            _t, _p = it
            if not (isinstance(_t, str) and _t) and not callable(_t):
                raise ValueError("TITLES: par deve ser (texto|callable, {props})")
            out.append({'TITLE': {'text': _t,
                                  **_check_props('TITLE', _p, '')}})
        elif isinstance(it, dict) and set(it) == {'TITLE'} and isinstance(it['TITLE'], dict):
            out.append({'TITLE': dict(it['TITLE'])})
        else:
            raise ValueError(
                "TITLES: item deve ser 'texto', callable, ('texto', {props}) "
                "ou {'TITLE': {...}}")
    if not out:
        raise ValueError("TITLES: exige ao menos um título")
    return {'TITLES': out}


def TEXT(text, props=None):
    """Factory pura: TEXT('...', {...}) == {'TEXT': {'text': '...', ...}}."""
    if not isinstance(text, str):
        raise ValueError("TEXT: texto deve ser str")
    return {'TEXT': {'text': text, **_check_props('TEXT', props or {}, '')}}


def TABS(*stops):
    """Factory pura: TABS(22, 48) == {'TABS': [22, 48]}; TABS() = restaura."""
    if len(stops) == 1 and isinstance(stops[0], (list, tuple)):
        stops = list(stops[0])
    else:
        stops = list(stops)
    return {'TABS': stops}


def IND(*bounds):
    """Factory pura: IND([l, r]) = região do fluxo; IND() = restaura."""
    if len(bounds) == 1 and isinstance(bounds[0], (list, tuple)):
        bounds = list(bounds[0])
    else:
        bounds = list(bounds)
    if bounds and len(bounds) != 2:
        raise ValueError("IND: exige [l, r] ou vazio (restaura)")
    return {'IND': bounds}


def FIELD(name, props=None):
    """Factory pura: FIELD('nome') == 'nome'; FIELD('n', {...}) == {'n': {...}}."""
    if not isinstance(name, str) or not name:
        raise ValueError("FIELD: nome deve ser str não vazia")
    if props is None:
        return name
    return {name: dict(_check_props('FIELD', props, ''))}


def _memo_check(width, recuo, label=''):
    """Valida `width`/`recuo` do `MEMO` — a MESMA regra na factory e no parse.

    Ficou aqui porque `parse_report` não passa items por `parse_report_item`
    (é construção de dataclass), e os dois call sites que passam — `_split_item`
    e `_expand_fields_list` — engolem `ValueError`. Ou seja: validação só no
    parse não dispara na declaração, que é onde ela tem que doer.
    """
    _q = f"report '{label}': " if label else ''
    if isinstance(width, bool) or not isinstance(width, (int, float)) or width <= 0:
        raise ValueError(f"{_q}'MEMO' exige 'width' cols > 0, veio {width!r}")
    if isinstance(recuo, bool) or not isinstance(recuo, (int, float)) or recuo < 0:
        raise ValueError(f"{_q}'MEMO' exige 'recuo' cols >= 0, veio {recuo!r}")
    # `recuo` afasta só a 1ª linha, então ela precisa de medida sobrando: recuo
    # >= width é erro de declaração, e sem este recuso o bloco sai degenerado
    # (uma palavra por linha).
    if recuo >= width:
        raise ValueError(
            f"{_q}'MEMO' recuo {recuo} >= width {width} — a 1ª linha "
            f"ficaria sem medida")


def MEMO(campo, width, props=None):
    """Factory pura: `MEMO('status', 80, {...})` — um FIELD com medida.

    `campo` aceita a MESMA gramática que `field_spec_item` (a de `FIELD`,
    `FIELDS` e `list.columns`): `'status'`, `('status', {props})`,
    `{'status': {props}}`, `{'field': 'status', **props}`. É a resposta a
    "por que o catálogo do status tinha que vir colado num `labels`, se a
    Entity já tem `options`?": não precisa. O catálogo é o override normal do
    field, e o label, o `calc` e a máscara vêm da Entity como em qualquer item
    de field — `MEMO` é um FIELD que quebra por palavra numa largura.

    Bloco de parágrafo: quebra numa medida (`width` em colunas da grade) e
    **centraliza na área livre** da zona. É o que o `IND` não fazia direito:
    `IND` abre uma zona que vaza para os itens seguintes e depende de ordem,
    enquanto `MEMO` tem a largura no próprio item.

    `campo` com `{` vira TEMPLATE (`MEMO('Prezado {fornecedor.nome}, ...')`) e
    aí não tem label nem override de catálogo — é a mesma distinção que separa
    `FIELD` de `TEXT`.

    Props: `align` (default `'J'` — parágrafo se justifica; `JUSTIFY_MAX` limita
    o quanto o espaço estica), `recuo` (cols, afasta **só a 1ª linha** — é
    `spaces(recuo) + texto`: a 1ª linha quebra na medida `w - recuo` e as
    seguintes na do bloco, então a borda direita continua reta), `font_size`,
    `font_style`, `label` (legenda acima do bloco, que NÃO se move com o
    recuo; no uso como field, o rótulo do campo), `when`.
    """
    _check_props('MEMO', props or {}, '')
    _memo_check(width, (props or {}).get('recuo', 0))
    from ajsystem.core.resolve import field_spec_item as _fsi
    achado = _fsi(campo)
    cfg = dict(props or {})
    if achado and '{' not in (achado[0] or ''):
        nome, overrides = achado
        # a gramática resolve o nome; os overrides do campo entram junto, como
        # em `FIELD('status', {'options': ...})`.
        return {'MEMO': {'field': nome, 'width': width, **overrides, **cfg}}
    if isinstance(campo, str):
        return {'MEMO': {'text': campo, 'width': width, **cfg}}
    raise ValueError(f"MEMO: campo deve ser nome de field ou template, veio {campo!r}")


def TEXTS(*items):
    """Factory pura: TEXTS('a', ('b', 'quando.c'), {'text': 'd', ...}).

    str = sempre; (texto, when) = par posicional exato; dict = props.
    """
    out = []
    for it in items:
        if isinstance(it, str):
            out.append({'TEXT': {'text': it}})
        elif isinstance(it, tuple):
            if len(it) != 2 or not isinstance(it[1], str):
                raise ValueError("TEXTS: par deve ser (texto|cfg, when)")
            if isinstance(it[0], str):
                out.append({'TEXT': {'text': it[0], 'when': it[1]}})
            elif isinstance(it[0], dict) and isinstance(it[0].get('text'), str):
                _cfg = dict(it[0])
                _cfg['when'] = it[1]
                out.append({'TEXT': _cfg})
            else:
                raise ValueError("TEXTS: par deve ser (texto|cfg, when)")
        elif isinstance(it, dict):
            out.append(it)
        else:
            raise ValueError("TEXTS: item deve ser str, par (texto, when) ou dict")
    return {'TEXTS': out}


def CR():
    """Factory pura: volta à 1ª coluna (sem avançar linha)."""
    return {'CR': {}}


def LF(n=1, props=None):
    """Factory pura: avança n linhas (default 1). `props` = `when` etc.

    O `when` aqui é o que permite um espaçamento que SOME junto com o bloco
    condicional ao redor — `LF(1, {'when': ...})`. Sem ele, o respiro ficaria
    para sempre num documento que não tem preâmbulo.
    """
    if isinstance(n, dict) and props is None:
        props, n = n, 1
    if isinstance(n, bool) or not isinstance(n, (int, float)) or n < 1:
        raise ValueError("LF: exige n >= 1")
    return {'LF': {'lines': n, **_check_props('LF', props or {}, '')}}


def FF():
    """Factory pura: quebra de página (só no corpo; no header = erro)."""
    return {'FF': {}}


def FIELDS(*items):
    """FIELDS('x', 'y', ('z', {props})) — itens de campo do report.

    item = 'campo' | ('campo', {props}). Cada item resolve como `columns`/
    `fields` de list/form: 'campo' simples, 'Entidade' expande a entidade,
    'Entidade.campo' campo relacionado. No dict, chaves de `Field`
    (`label/width/align/mask/decimals/percent`) são override do field;
    as demais (`tab/location/pos/rows_before/rows_after/when/font*/function`)
    são overlay de report.
    """
    norm = []
    for it in items:
        # `FIELDS` aceita só as duas formas curtas: a forma longa (dict) é das
        # props que recebem lista solta. A DECISÃO ("isto nomeia um field?") é a
        # genérica; a política (recusar) é do factory.
        achado = None if isinstance(it, dict) else field_spec_item(it)
        if achado is None:
            raise ValueError("FIELDS: item deve ser 'campo' ou ('campo', {props})")
        nome, props = achado
        if not nome:
            raise ValueError("FIELDS: nome de campo não pode ser vazio")
        norm.append(nome if not props else (nome, props))
    if not norm:
        raise ValueError("FIELDS: exige ao menos um campo")
    return {'FIELDS': {'items': norm}}


def FONT(name=None, cpp=None):
    """Factory pura: FONT() = restaura; FONT('DRAFT') | FONT('Courier', 0).

    Nome de preset (catálogo framework/app/página) ou família crua (aí cpp
    é obrigatório). Tradução 1:1 validada pelo normalizador.
    """
    if name is None and cpp is None:
        return {'FONT': {}}
    if not isinstance(name, str) or not name:
        raise ValueError("FONT: nome deve ser str não vazia")
    if cpp is not None and cpp not in (0, 1, 2, 3):
        raise ValueError("FONT: cpp deve ser 0|1|2|3 (10/12/17/20cpp)")
    cfg = {'font': name}
    if cpp is not None:
        cfg['cpp'] = cpp
    return {'FONT': cfg}


def POS(*where):
    """Factory pura: POS(22, 0) == {'POS': [22, 0]} (ou POS([22, 0]))."""
    if len(where) == 1 and isinstance(where[0], (list, tuple)):
        where = list(where[0])
    else:
        where = list(where)
    if len(where) != 2:
        raise ValueError("POS: exige [col, lin]")
    return {'POS': where}


def _located(kind, *args, **kw):
    """`LINE`/`BOX`/`CIRCLE`: coordenada posicional, `when` e props.

    Variádica como `TABS`/`IND`/`POS` (uma lista solta ainda vale), porque a
    grade é declarada em números — `LINE(10, 5, 20)`, não `LINE([10, 5, 20])`.
    Um `str` final é o `when`; um `dict` final são `props` (legado).

    `LINE` aceita ainda as formas sem coordenada, que só o render resolve
    (dependem do cursor): `LINE()` = zona/tabela, `LINE(True)` = página
    inteira, `LINE(w)` = `w` cols a partir do cursor. `BOX`/`CIRCLE` são
    desenhados por extensão e não têm essa família.
    """
    args = list(args)
    when, props = None, {}
    if args and isinstance(args[-1], str):
        when = args.pop()
    elif args and isinstance(args[-1], dict):
        props = dict(args.pop())
    for _k in list(kw):
        raise ValueError(f"{kind}: prop {_k!r} desconhecida (use o `when` final)")
    cfg = dict(props)

    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        cfg['location'] = list(args[0])
    elif kind == 'LINE' and not args and 'location' not in cfg:
        cfg['mode'] = 'zona'
    elif kind == 'LINE' and args and isinstance(args[0], bool):
        cfg['mode'] = 'pagina' if args[0] else 'zona'
    elif kind == 'LINE' and len(args) == 1:
        cfg['mode'], cfg['width'] = 'cursor', args[0]   # LINE(w) ≡ LINE(PCOL, PROW, w)
    elif args:
        # LINE completa com 0 (omissão = extensão nula); BOX/CIRCLE guardam o
        # comprimento declarado, porque o 4º ausente tem outro sentido para cada
        # um: altura = largura (quadrado) e achata compensado.
        cfg['location'] = ([0] * 4 if kind == 'LINE' else list(args))
        if kind == 'LINE':
            for _i, _v in enumerate(args):
                cfg['location'][_i] = _v
    elif 'location' not in cfg and 'mode' not in cfg:
        raise ValueError(f"{kind}: informe a coordenada")

    if when is not None:
        cfg['when'] = when
    return {kind: cfg}


def LINE(*args):
    """Factory pura. Formas:

        LINE()                        = largura da zona (IND) ou da tabela
        LINE(True|False)              = largura da página / da zona
        LINE(w)                       = w colunas a partir do cursor (PCOL, PROW)
        LINE(c, r)                    = ponto em (c, r)
        LINE(c, r, cols)              = horizontal: até (c+cols, r)
        LINE(c, r, 0, rows)           = vertical:   até (c, r+rows)
        LINE(c, r, cols, rows)        = inclinada:  até (c+cols, r+rows)
        LINE(..., 'queda')            = só quando `queda` é verdadeira

    O 3º e 4º são DELTAS (extensão), não posição final. `LINE([c, r, cols])`
    continua valendo, como em `TABS`/`IND`/`POS`. Desenha e avança uma linha.
    """
    return _located('LINE', *args)


def BOX(*args):
    """Factory pura: BOX(c, r, cols[, rows]) ou BOX([c, r, cols[, rows]])."""
    return _located('BOX', *args)


def CIRCLE(*args):
    """Factory pura: CIRCLE(c, r, raio[, achata]) ou CIRCLE([c, r, raio[, achata]]).

    `raio` em cols; `achata` 0/ausente = círculo compensado, >0 achata a
    altura por esse fator, <0 achata a largura.
    """
    return _located('CIRCLE', *args)


def IMAGE(field, props=None):
    """Factory pura: IMAGE('foto', {...}) == {'IMAGE': {'field': 'foto', ...}}."""
    if not isinstance(field, str) or not field:
        raise ValueError("IMAGE: field deve ser str não vazia")
    return {'IMAGE': {'field': field, **_check_props('IMAGE', props or {}, '')}}


def parse_report_item(it, label='') -> ReportItem:
    """Normaliza 1 item -> ReportItem (fail-fast)."""
    if isinstance(it, str):
        if it.isupper():
            if it not in ITEM_KINDS:
                raise ValueError(f"report '{label}': elemento '{it}' desconhecido")
            return ReportItem(kind=it, name=it, config={})
        return ReportItem(kind='FIELD', name=it, config={})
    if isinstance(it, dict):
        if 'field' in it:
            return ReportItem(kind='FIELD', name=it.get('field'),
                              config={k: v for k, v in it.items() if k != 'field'})
        if len(it) == 1:
            (k, v), = it.items()
            if k.isupper():
                if k not in ITEM_KINDS:
                    raise ValueError(f"report '{label}': elemento '{k}' desconhecido")
                if k in ('TABS', 'POS'):
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': '{k}' exige lista")
                    return ReportItem(kind=k, name=k, config={'values': v})
                if k == 'IND':
                    if not isinstance(v, list) or (v and len(v) != 2):
                        raise ValueError(f"report '{label}': 'IND' exige [l, r] ou []")
                    return ReportItem(kind=k, name=k, config={'values': list(v)})
                if k == 'FONT':
                    if not isinstance(v, dict) or not v.get('font'):
                        raise ValueError(f"report '{label}': 'FONT' exige {{font, ...}}")
                    if 'cpp' in v and v['cpp'] not in (0, 1, 2, 3):
                        raise ValueError(f"report '{label}': cpp deve ser 0|1|2|3")
                    return ReportItem(kind=k, name=k, config=v)
                if k == 'FIELDS':
                    if not isinstance(v, dict):
                        raise ValueError(f"report '{label}': 'FIELDS' exige dict")
                    return ReportItem(kind=k, name=k, config=v)
                if k == 'TEXTS':
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': 'TEXTS' exige lista")
                    return ReportItem(kind=k, name=k, config={'items': list(v)})
                if k == 'TITLES':
                    # A lista entra inteira: quem consome é o renderizador, que
                    # precisa da ORDEM para a cascata (1º = título, demais =
                    # subtítulo). Validar entrada a entrada aqui é o que dá o
                    # erro na declaração em vez de no meio do PDF.
                    if not isinstance(v, list) or not v:
                        raise ValueError(f"report '{label}': 'TITLES' exige lista não vazia")
                    for _i, _sub in enumerate(v):
                        if isinstance(_sub, dict) and set(_sub) == {'TITLE'} \
                                and isinstance(_sub['TITLE'], dict):
                            continue
                        if not ((isinstance(_sub, str) and _sub) or callable(_sub)):
                            raise ValueError(
                                f"report '{label}': TITLES[{_i}] deve ser 'texto', "
                                f"callable ou {{'TITLE': {{...}}}}")
                    # `list(v)`, e não copia: o apply anexa `_fmt_opts` na
                    # entrada pelo dict de origem, e uma cópia aqui faria o
                    # catálogo sumir (o `{status}` sairia com o código).
                    return ReportItem(kind=k, name=k, config={'items': list(v)})
                if k == 'MEMO':
                    if not isinstance(v, dict):
                        raise ValueError(f"report '{label}': 'MEMO' exige dict")
                    _memo_check(v.get('width'), v.get('recuo', 0), label)
                    # `field` = FIELD com medida (a forma normal) · `text` =
                    # TEMPLATE. Exige um dos dois, senão o bloco sai vazio e o
                    # autor não descobre por quê.
                    _f, _t = v.get('field'), v.get('text')
                    if not isinstance(_f, str) and not isinstance(_t, str):
                        raise ValueError(
                            f"report '{label}': 'MEMO' exige 'field' (nome de field) "
                            f"ou 'text' (template)")
                    return ReportItem(kind=k, name=k, config=v)
                if k in ('CR', 'FF'):
                    return ReportItem(kind=k, name=k, config={})
                if k == 'LF':
                    _lines = 1 if not isinstance(v, dict) else v.get('lines', 1)
                    if isinstance(_lines, bool) or not isinstance(_lines, (int, float)) or _lines < 1:
                        raise ValueError(f"report '{label}': 'LF' exige lines >= 1")
                    return ReportItem(kind=k, name=k, config={'lines': _lines})
                if not isinstance(v, dict):
                    raise ValueError(f"report '{label}': cfg de '{k}' deve ser dict")
                return ReportItem(kind=k, name=k, config=v)
            if not isinstance(v, dict):
                raise ValueError(f"report '{label}': cfg de '{k}' deve ser dict")
            return ReportItem(kind='FIELD', name=k, config=v)
    raise ValueError(f"report '{label}': item deve ser str ou dict, veio {it!r}")


@dataclass
class ReportColumn:
    """Coluna da tabela no relatório."""
    field: str
    label: Optional[str] = None
    width: Optional[float] = None
    align: str = 'left'
    format: Optional[str] = None
    agg: Optional[str] = None
    function: Optional[Callable] = None
    # Montagem via template '{campo}' (ex. código '1.01.001'); suppress em
    # branco repetido na célula (place=0 do groups). Quebras vão em
    # table.groups (só o que imprime entra em columns).
    text: Optional[str] = None
    suppress: bool = False

    def __post_init__(self):
        if self.label is None:
            self.label = self.field


class ReportColumns:
    """Dict de dicts -> lista de ReportColumn. Ordem preservada."""

    def __init__(self, columns: dict):
        self._columns = [
            ReportColumn(field=name, **(cfg or {}))
            for name, cfg in columns.items()
        ]

    def __iter__(self):
        return iter(self._columns)

    def __len__(self):
        return len(self._columns)


@dataclass
class ReportGroup:
    """Configuração de agrupamento - cada grupo = tabela separada."""
    field: str
    label: Optional[str] = None
    position: str = 'titulo'
    subtotal: bool = True
    total: bool = True
    fecha_tabela: bool = False
    nova_pagina: bool = False


@dataclass
class ReportText:
    """Texto avulso no relatório."""
    text: str
    font_size: int = 10
    font_style: str = ''
    align: str = 'L'
    when: str = 'end_of_report'


@dataclass
class ReportBody:
    """Corpo de um relatório: datasource + formato de impressão.

    `source` define DE ONDE vêm os dados (entity string, dict com filtros ou um
    `Query`). `form` e `table` são formatos de impressão MUTUAMENTE EXCLUSIVOS:
      - `form`:  impressão campo/valor posicionado na página (reservado p/ futuro);
      - `table`: tabela com `columns` + `hierarchy` (níveis visuais de quebra).
    `before`/`after` são linhas impressas antes/depois do formato.
    """
    source: Optional[Union[str, dict, object]] = None
    form: Optional[dict] = None
    table: Optional[dict] = None
    before: Optional[object] = None
    after: Optional[object] = None
    # Filtro aplicado pelo motor na query (dict de igualdade `{campo: valor}`
    # ou callable). O valor pode vir da request na impressão (ex.: tipo).
    filter: Optional[Union[dict, Callable]] = None
    # Numeração hierárquica (apresentação, genérica): {using, pk, parent,
    # group, root, child, target, maxdepth}. Ver QPLANO/PLANO no app.
    levels: Optional[dict] = dc_field(default=None)
    # Itens inline em ordem (string=field, minúscula=field+overrides,
    # MAIÚSCULA=elemento TEXT/IMAGE/LINE/BOX/CIRCLE). Render antes da tabela.
    items: Optional[list] = dc_field(default=None)

    def __post_init__(self):
        formats = [k for k in ('form', 'table') if getattr(self, k) is not None]
        if len(formats) > 1:
            raise ValueError("ReportBody: defina 'form' OU 'table', não ambos.")


@dataclass
class Report:
    """Configuração completa de um relatório PDF.

    Seções (forma declarativa `dict`):
      - header: dict com config do cabeçalho (logo, título, fields)
      - body:   dict do `ReportBody` (datasource + formato de impressão)
      - footer: dict do rodapé de página (report_footer, show_*, footer_*)
    """
    label: str

    # Página
    page_size: str = 'A4'
    orientation: str = 'portrait'

    # Header (dict consolidado)
    header: Optional[dict] = dc_field(default=None)

    # Body (datasource + formato de impressão) — ReportBody | dict
    body: Optional[ReportBody] = dc_field(default=None)

    # Report footer (última linha de cada página) — dict consolidado
    # Chaves: text, show_user, show_datetime, show_company, show_page_number,
    #         separator, align, font_size. Todos default False (exceto text).
    footer: Optional[dict] = None

    # Texts avulsos
    texts: Optional[list] = None

    # Template standalone e logo saíram da declaração (motor/APP resolvem;
    # chaves legadas ignoradas no parse). Ver PRINT_TEMPLATE/APP.logo.

    # Margens (mm)
    margin_top: float = 10
    margin_bottom: float = 20
    margin_left: float = 10
    margin_right: float = 10
    auto_page_break: bool = True

    # Linhas horizontais internas da tabela (entre linhas de dados e GroupRow)
    show_table_lines: bool = False

    # Formato novo (ponto 1 travado): página/sessão/elementos em grade.
    # Passthrough nesta fase (pdf ainda renderiza fluxo); parse_report aceita
    # os dois formatos, legado tem precedência quando ambos presentes.
    page: Optional[dict] = dc_field(default=None)
    session: Optional[dict] = dc_field(default=None)
    shapes: Optional[list] = dc_field(default=None)


def parse_report(spec):
    """dict | Report → Report (idempotente).

    Relatórios são declarados como dict puro no app
    (`FOO_REPORT = {...}`); o motor resolve para Report aqui.
    """
    if isinstance(spec, Report):
        return spec
    if isinstance(spec, dict):
        spec = dict(spec)
        # Shim: chaves removidas (fragmento sempre overlay; template/logo no
        # motor/APP). Dicts antigos seguem parseando sem TypeError.
        spec.pop('print_fragment_template', None)
        spec.pop('print_template', None)
        spec.pop('logo_path', None)
        spec.pop('orientation_mutable', None)
        body = spec.get('body')
        if isinstance(body, dict):
            spec['body'] = ReportBody(**body)
        return Report(**spec)
    raise TypeError(f"report deve ser dict ou Report, recebeu {type(spec).__name__}: {spec!r}")
