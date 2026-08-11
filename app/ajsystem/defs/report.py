"""Configuração declarativa de relatórios PDF (genérico do framework).

Cada sistema declara relatórios via:

    REP = Report(label='...', header={...}, table={...})

E o motor `ajsystem.core.pdf.gerar_pdf_relatorio(report, ...)` os renderiza.
"""
from dataclasses import dataclass, field as dc_field
from typing import Optional, Callable


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
    aggregate: Optional[str] = None
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


_HEADER_DEFAULTS = {
    'logo': {'position': 'N', 'lines': 2},
    'titulo': {'label': None, 'align': 'C', 'font_style': 'B', 'font_size': 16},
    'subtitle': None,
    'fields': None,
    'field_columns': 2,
    'on_each_page': True,
    'layout': 'centered',
}


@dataclass
class Report:
    """Configuração completa de um relatório PDF.

    Seções:
      - header: dict com config do cabeçalho (logo, título, campos)
      - before_table: lista de linhas ou callable antes da tabela
      - table: dict com config da tabela (columns, footer, after)
      - after_table: lista de linhas ou callable depois da tabela
      - footer: rodapé de página (report_footer, show_*, footer_*)
    """
    label: str
    endpoint: Optional[str] = None

    # Página
    page_size: str = 'A4'
    orientation: str = 'portrait'
    orientation_mutable: bool = False

    # Header (dict consolidado)
    header: Optional[dict] = dc_field(default=None)

    # Table (dict consolidado)
    table: Optional[dict] = dc_field(default=None)

    # Report footer (última linha de cada página) — dict consolidado
    # Chaves: text, show_user, show_datetime, show_company, show_page_number,
    #         separator, align, font_size. Todos default False (exceto text).
    footer: Optional[dict] = None

    # Before / after table (list of line dicts or callable)
    before_table: Optional[object] = None
    after_table: Optional[object] = None

    # Texts avulsos
    texts: Optional[list] = None

    # Template de impressão HTML (wrapper com iframe + botão Voltar)
    print_template: str = 'components/print_default.html'
    # Endpoint de edição para fallback do botão Voltar (ex: 'compras.edit')
    edit_endpoint: Optional[str] = None

    # Margens (mm)
    margin_top: float = 10
    margin_bottom: float = 20
    margin_left: float = 10
    margin_right: float = 10
    auto_page_break: bool = True

    # Ordem dos dados no relatório (field name). None = ordem original.
    ordem: Optional[str] = None

    # Níveis visuais de GroupRow. Lista de dicts com bg=(R,G,B), size, bold, indent.
    # Ex: [{'bg': (240,240,240), 'size': 10, 'bold': True, 'indent': 2}]
    groups: Optional[list] = None

    # Função que retorna os dados do relatório (callable sem argumentos)
    data_fn: Optional[callable] = None

    # Linhas horizontais internas da tabela (entre linhas de dados e GroupRow)
    show_table_lines: bool = False

    def _build_header(self) -> '_ReportHeader':
        h = {**_HEADER_DEFAULTS, **(self.header or {})}

        # Logo: nested (deep merge) ou flat
        logo_cfg = {**_HEADER_DEFAULTS.get('logo', {}), **(h.get('logo') or {})}
        pos = logo_cfg.get('position', h.get('logo_align', 'N'))
        show_logo = pos != 'N'
        logo_lines = logo_cfg.get('lines', 4)
        logo_align = 'C' if pos == 'N' else pos

        # Título: nested (deep merge) ou flat
        titulo_cfg = {**_HEADER_DEFAULTS.get('titulo', {}), **(h.get('titulo') or {})}
        title = titulo_cfg.get('label') or h.get('title') or self.label
        title_font_size = titulo_cfg.get('font_size', h.get('title_font_size', 16))
        title_font_style = titulo_cfg.get('font_style', h.get('title_font_style', 'B'))
        title_align = titulo_cfg.get('align', h.get('title_align', 'C'))

        # Subtítulo: dict, str ou None
        sub_cfg = h.get('subtitle')
        if isinstance(sub_cfg, dict):
            subtitle = sub_cfg.get('label')
            subtitle_font_size = sub_cfg.get('font_size', h.get('subtitle_font_size', 10))
            subtitle_align = sub_cfg.get('align', h.get('subtitle_align', 'C'))
        else:
            subtitle = sub_cfg
            subtitle_font_size = h.get('subtitle_font_size', 10)
            subtitle_align = h.get('subtitle_align', 'C')

        return _ReportHeader(
            show_logo=show_logo,
            logo_path=h.get('logo_path'),
            logo_width=h.get('logo_width'),
            logo_height=logo_lines * 6 if show_logo else 0,
            logo_align=logo_align,
            title=title,
            title_font_size=title_font_size,
            title_font_style=title_font_style,
            title_align=title_align,
            subtitle=subtitle,
            subtitle_font_size=subtitle_font_size,
            subtitle_align=subtitle_align,
            fields=h.get('fields'),
            field_columns=h.get('field_columns', 2),
            on_each_page=h.get('on_each_page', True),
            layout=h.get('layout', 'centered'),
        )

    def _build_table(self) -> '_ReportTable':
        t = self.table or {}
        columns = t.get('columns')
        if isinstance(columns, dict):
            columns = ReportColumns(columns)
        return _ReportTable(
            columns=columns,
            footer=t.get('footer', False),
            footer_label=t.get('footer_label', 'Total'),
            after=t.get('after'),
            lines_before=t.get('lines_before', 0),
            lines_after=t.get('lines_after', 0),
        )

    def _build_footer(self) -> '_ReportFooter':
        f = self.footer or {}
        return _ReportFooter(
            text=f.get('text'),
            show_user=f.get('show_user', False),
            show_datetime=f.get('show_datetime', False),
            show_company=f.get('show_company', False),
            show_page_number=f.get('show_page_number', False),
            separator=f.get('separator', ' | '),
            align=f.get('align', 'C'),
            font_size=f.get('font_size', 8),
        )


@dataclass
class _ReportHeader:
    """Cabeçalho do relatório (interno)."""
    show_logo: bool = True
    logo_path: Optional[str] = None
    logo_width: Optional[float] = None
    logo_height: float = 24
    logo_align: str = 'C'
    title: Optional[str] = None
    title_font_size: int = 16
    title_font_style: str = 'B'
    title_align: str = 'C'
    subtitle: Optional[str] = None
    subtitle_font_size: int = 10
    subtitle_align: str = 'C'
    fields: Optional[list] = None
    field_columns: int = 2
    on_each_page: bool = True
    layout: str = 'centered'


@dataclass
class _ReportTable:
    """Tabela do relatório (interno)."""
    columns: ReportColumns = None
    footer: bool = False
    footer_label: str = 'Total'
    after: Optional[object] = None
    lines_before: int = 0
    lines_after: int = 0


@dataclass
class _ReportFooter:
    """Rodapé de página (interno)."""
    text: Optional[object] = None
    show_user: bool = False
    show_datetime: bool = False
    show_company: bool = False
    show_page_number: bool = False
    separator: str = ' | '
    align: str = 'C'
    font_size: int = 8
