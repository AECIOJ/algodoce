"""Configuração declarativa de relatórios PDF (genérico do framework).

Cada sistema declara relatórios via:

    REP = Report(label='...', header={...}, body={...})

E o motor `ajsystem.core.pdf.gerar_pdf_relatorio(report, ...)` os renderiza.
"""
from dataclasses import dataclass, field as dc_field
from typing import Optional, Callable, Union


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

    # Template de impressão HTML (fragmento p/ injeção e página standalone)
    print_template: str = 'components/print_default.html'
    print_fragment_template: str = 'components/print_fragment.html'
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


def parse_report(spec):
    """dict | Report → Report (idempotente).

    Relatórios são declarados como dict puro no app
    (`FOO_REPORT = {...}`); o motor resolve para Report aqui.
    """
    if isinstance(spec, Report):
        return spec
    if isinstance(spec, dict):
        spec = dict(spec)
        body = spec.get('body')
        if isinstance(body, dict):
            spec['body'] = ReportBody(**body)
        return Report(**spec)
    raise TypeError(f"report deve ser dict ou Report, recebeu {type(spec).__name__}: {spec!r}")
