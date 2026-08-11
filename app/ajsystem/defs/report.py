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
