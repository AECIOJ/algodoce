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
    'LOGO', 'TITLE', 'TEXT', 'TABS', 'IND', 'FIELD', 'TEXTS',
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
              'TABS', 'POS', 'FIELDS', 'FONT', 'IND', 'TEXTS', 'CR', 'LF', 'FF')


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


def LF(n=1):
    """Factory pura: avança n linhas (default 1)."""
    if isinstance(n, bool) or not isinstance(n, (int, float)) or n < 1:
        raise ValueError("LF: exige n >= 1")
    return {'LF': {'lines': n}}


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


def _located(kind, location, props, label=''):
    if not isinstance(location, (list, tuple)):
        raise ValueError(f"{kind}: location deve ser lista")
    return {kind: {'location': list(location), **_check_props(kind, props or {}, label)}}


def LINE(location, props=None):
    """Factory pura: LINE([...], {...}) == {'LINE': {'location': [...], ...}}."""
    return _located('LINE', location, props)


def BOX(location, props=None):
    """Factory pura: BOX([...], {...}) == {'BOX': {'location': [...], ...}}."""
    return _located('BOX', location, props)


def CIRCLE(location, props=None):
    """Factory pura: CIRCLE([...], {...}) == {'CIRCLE': {'location': [...], ...}}."""
    return _located('CIRCLE', location, props)


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
