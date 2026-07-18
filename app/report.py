"""
XXX_REPORT — Configuração de relatórios PDF.

Cada rota ou módulo de relatório declara:
  XXX_REPORT = Report(label='...', header={...}, table={...})

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Report — configuração completa
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Campo             Tipo         Default     Descrição
 ───────────────── ──────────── ─────────── ──────────────────────────────
 label             str          (obrig.)    Título do relatório
 endpoint          str          None        Endpoint de geração
 page_size         str          'A4'        Tamanho da página
 orientation       str          'portrait'  'portrait' | 'landscape'
 orientation_mutable bool       False       Usuário pode mudar orientação
 header            dict         None        Config do cabeçalho (ver abaixo)
 table             dict         None        Config da tabela (ver abaixo)
 report_footer     object       None        Texto do rodapé de página
 show_user         bool         False       Exibir usuário no rodapé
 show_datetime     bool         True        Exibir data/hora no rodapé
 show_company      bool         False       Exibir empresa no rodapé
 show_page_number  bool         True        Exibir número da página
 footer_separator  str          ' | '       Separador dos itens do rodapé
 footer_align      str          'C'         Alinhamento do rodapé
 footer_font_size  int          8           Tamanho da fonte do rodapé
 texts             list         None        Textos avulsos (ver ReportText)
 margin_top        float        10          Margem superior (mm)
 margin_bottom     float        20          Margem inferior (mm)
 margin_left       float        10          Margem esquerda (mm)
 margin_right      float        10          Margem direita (mm)
 auto_page_break   bool         True        Quebra automática de página

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 header (dict)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Chave             Tipo         Default     Descrição
 ───────────────── ──────────── ─────────── ──────────────────────────────
 layout            str          'centered'  'centered' | 'logo_left'
 title             str          label       Título (suporta {id}, {campo})
 title_font_size   int          16          Tamanho do título
 title_font_style  str          'B'         Estilo: '' normal, 'B' bold
 title_align       str          'C'         'L' | 'C' | 'R'
 subtitle          str          None        Subtítulo
 subtitle_font_size int         10
 subtitle_align    str          'C'
 show_logo         bool         True        Exibir logotipo
 logo_path         str          None        Caminho da imagem (None=padrão)
 logo_width        float        None        Largura do logo (mm)
 logo_align        str          'C'         Alinhamento do logo
 fields            list[dict]   None        Lista de campos do cabeçalho
 field_columns     int          2           Colunas de campos
 on_each_page      bool         True        Repetir em cada página

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 header.fields (lista de dicts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Chave      Tipo       Descrição
 ────────── ────────── ────────────────────────────────────────────────
 field      str        Nome do campo do model (acesso aninhado: 'conta.nome')
 label      str        Rótulo do campo
 align      str        'left' | 'right' | 'center'
 format     str        'datetime' | 'date' | 'brl' | None
 function   callable   Função customizada: f(item) -> str

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 table (dict)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Chave        Tipo         Default   Descrição
 ──────────── ──────────── ───────── ──────────────────────────────────
 columns      dict         (obrig.)  Dict de colunas (ver abaixo)
 groups       list[dict]   None      Lista de ReportGroup
 footer       bool         False     Exibir rodapé da tabela (totais)
 footer_label str          'Total'   Label do total
 after        callable     None      Função p/ texto após a tabela

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 table.columns (dict de dicts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Chave      Tipo       Descrição
 ────────── ────────── ────────────────────────────────────────────────
 label      str        Título da coluna
 width      float      Largura da coluna (mm)
 align      str        'left' | 'right' | 'center'
 format     str        'brl' | 'datetime' | 'date' | None
 aggregate  str        'sum' | None
 function   callable   f(item) -> valor

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Exemplo
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 ORCAMENTO_REPORT = Report(
     label='Orçamento',
     header={
         'layout': 'logo_left',
         'title': 'Orçamento #{id}',
         'fields': [
             {'field': 'cliente_nome', 'label': 'Cliente'},
             {'field': 'data_pedido', 'label': 'Data', 'align': 'right', 'format': 'datetime'},
             {'label': 'Validade', 'align': 'right', 'function': _validade_text},
         ],
     },
     table={
         'columns': {
             'product.nome':   {'label': 'Produto', 'width': 50},
             'quantidade':     {'label': 'Qtd.', 'width': 10, 'align': 'center'},
             'preco_unitario': {'label': 'Preço', 'width': 20, 'align': 'right', 'format': 'brl'},
             'valor':          {'label': 'Valor', 'width': 20, 'align': 'right', 'format': 'brl',
                                'function': _valor_item, 'aggregate': 'sum'},
         },
         'footer': True,
         'footer_label': 'Total',
         'after': _forminhas_carteira,
     },
 )
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
    'show_logo': True,
    'logo_width': None,
    'logo_align': 'C',
    'layout': 'centered',
    'title_font_size': 16,
    'title_font_style': 'B',
    'title_align': 'C',
    'subtitle': None,
    'subtitle_font_size': 10,
    'subtitle_align': 'C',
    'fields': None,
    'field_columns': 2,
    'on_each_page': True,
}


@dataclass
class Report:
    """Configuração completa de um relatório PDF.

    Seções:
      - header: dict com config do cabeçalho (logo, título, campos)
      - before_table: lista de linhas ou callable antes da tabela
      - table: dict com config da tabela (columns, groups, footer, after)
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

    # Report footer (última linha de cada página)
    report_footer: Optional[object] = None
    show_user: bool = False
    show_datetime: bool = True
    show_company: bool = False
    show_page_number: bool = True
    footer_separator: str = ' | '
    footer_align: str = 'C'
    footer_font_size: int = 8

    # Before / after table (list of line dicts or callable)
    before_table: Optional[object] = None
    after_table: Optional[object] = None

    # Texts avulsos
    texts: Optional[list] = None

    # Margens (mm)
    margin_top: float = 10
    margin_bottom: float = 20
    margin_left: float = 10
    margin_right: float = 10
    auto_page_break: bool = True

    def _build_header(self) -> '_ReportHeader':
        h = {**_HEADER_DEFAULTS, **(self.header or {})}
        title = h.get('title') or self.label
        return _ReportHeader(
            show_logo=h.get('show_logo', True),
            logo_path=h.get('logo_path'),
            logo_width=h.get('logo_width'),
            logo_align=h.get('logo_align', 'C'),
            title=title,
            title_font_size=h.get('title_font_size', 16),
            title_font_style=h.get('title_font_style', 'B'),
            title_align=h.get('title_align', 'C'),
            subtitle=h.get('subtitle'),
            subtitle_font_size=h.get('subtitle_font_size', 10),
            subtitle_align=h.get('subtitle_align', 'C'),
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
        groups = t.get('groups')
        if groups:
            groups = [ReportGroup(**g) if isinstance(g, dict) else g for g in groups]
        return _ReportTable(
            columns=columns,
            groups=groups,
            footer=t.get('footer', False),
            footer_label=t.get('footer_label', 'Total'),
            after=t.get('after'),
        )

    def _build_footer(self) -> '_ReportFooter':
        return _ReportFooter(
            text=self.report_footer,
            show_user=self.show_user,
            show_datetime=self.show_datetime,
            show_company=self.show_company,
            show_page_number=self.show_page_number,
            separator=self.footer_separator,
            align=self.footer_align,
            font_size=self.footer_font_size,
        )


@dataclass
class _ReportHeader:
    """Cabeçalho do relatório (interno)."""
    show_logo: bool = True
    logo_path: Optional[str] = None
    logo_width: Optional[float] = None
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
    groups: Optional[list] = None
    footer: bool = False
    footer_label: str = 'Total'
    after: Optional[object] = None


@dataclass
class _ReportFooter:
    """Rodapé de página (interno)."""
    text: Optional[object] = None
    show_user: bool = False
    show_datetime: bool = True
    show_company: bool = False
    show_page_number: bool = True
    separator: str = ' | '
    align: str = 'C'
    font_size: int = 8
