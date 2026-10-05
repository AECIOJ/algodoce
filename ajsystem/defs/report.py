"""Configuração declarativa de relatórios PDF (genérico do framework).

Cada sistema declara relatórios via:

    REP = Report(label='...', header={...}, body={...})

E o motor `ajsystem.core.pdf.gerar_pdf_relatorio(report, ...)` os renderiza.
"""
from dataclasses import dataclass, field as dc_field
from typing import Optional, Callable, Union


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
              'TABS', 'POS', 'FIELDS')


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
    """Factory pura: TABS(22, 48) == {'TABS': [22, 48]} (ou TABS([22, 48]))."""
    if len(stops) == 1 and isinstance(stops[0], (list, tuple)):
        stops = list(stops[0])
    else:
        stops = list(stops)
    if not stops:
        raise ValueError("TABS: exige ao menos uma parada")
    return {'TABS': stops}


def FIELD(name, props=None):
    """Factory pura: FIELD('nome') == 'nome'; FIELD('n', {...}) == {'n': {...}}."""
    if not isinstance(name, str) or not name:
        raise ValueError("FIELD: nome deve ser str não vazia")
    if props is None:
        return name
    return {name: dict(_check_props('FIELD', props, ''))}


def FIELDS(source, when=None):
    """Factory pura: FIELDS('Evento', when='evento') | FIELDS(['a','b'], when=...).

    source = relação/model (expande a Entity) ou lista explícita. when =
    path avaliado truthy (ausente = sempre). Tradução 1:1 validada igual.
    """
    if isinstance(source, str):
        if not source:
            raise ValueError("FIELDS: source deve ser relação/lista não vazia")
    elif isinstance(source, (list, tuple)):
        if not source or not all(isinstance(s, str) and s for s in source):
            raise ValueError("FIELDS: lista deve ter strs não vazias")
        source = list(source)
    else:
        raise ValueError("FIELDS: source deve ser str ou lista")
    if when is not None and (not isinstance(when, str) or not when):
        raise ValueError("FIELDS: when deve ser path str")
    cfg = {'source': source}
    if when is not None:
        cfg['when'] = when
    return {'FIELDS': cfg}


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
                if k == 'FIELDS':
                    if not isinstance(v, dict):
                        raise ValueError(f"report '{label}': 'FIELDS' exige dict")
                    return ReportItem(kind=k, name=k, config=v)
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
    orientation_mutable: bool = False

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

    # Template de impressão HTML (página standalone). O fragmento injetado
    # é sempre o overlay do framework (fragmento + alternância do container);
    # a chave legada 'print_fragment_template' é ignorada no parse (shim).
    print_template: str = 'components/print_default.html'
    # Path da logo (relativo ao root_path do app; resolvido em runtime)
    logo_path: str = 'static/icons/Logo.png'

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
        # Shim: 'print_fragment_template' removida (fragmento sempre overlay);
        # dicts antigos com a chave seguem parseando sem TypeError.
        spec.pop('print_fragment_template', None)
        body = spec.get('body')
        if isinstance(body, dict):
            spec['body'] = ReportBody(**body)
        return Report(**spec)
    raise TypeError(f"report deve ser dict ou Report, recebeu {type(spec).__name__}: {spec!r}")
