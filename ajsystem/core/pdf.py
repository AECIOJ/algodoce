"""Motor de geração de PDF a partir de configuração `Report` (genérico).

O sistema host declara `Report` (ver `ajsystem.defs.report`) e chama
`gerar_pdf_relatorio(report, data, instance=...)`. Formatação BRL/data são
embutidas; sem dependência de modelos da aplicação.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from flask_login import current_user
from fpdf import FPDF

from ajsystem.core.utils import apply_transform, fmt_money, normalize_currency
from ajsystem.defs.report import (
    Report, ReportField, ReportColumn, ReportColumns, ReportGroup,
    ReportText, parse_header_field,
)


_HEADER_DEFAULTS = {
    'logo': {'position': 'N', 'lines': 2},
    'title': {'label': None, 'align': 'C', 'font_style': 'B', 'font_size': 16},
    'subtitle': None,
    'fields': None,
    'field_columns': 2,
    'on_each_page': True,
    'layout': 'centered',
}


@dataclass
class _ReportHeader:
    """Cabeçalho do relatório (interno de renderização)."""
    show_logo: bool = True
    logo_path: Optional[str] = None
    logo_width: Optional[float] = None
    logo_height: float = 24
    logo_align: str = 'C'
    logo_location: Optional[list] = None
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
    line: bool = False              # linha horizontal após o cabeçalho
    raw_header: Optional[list] = None  # forma lista (header=[...]); None = dict legado


TOTALS_DEFAULT_LABEL = 'Total'
TOTALS_FUNCS = ('sum', 'count', 'avg', 'min', 'max')


def _agg_apply(fn, values):
    """Aplica função de total sobre valores (None ignorado; vazio -> 0/'—')."""
    vals = [v for v in (values or []) if v is not None]
    if fn == 'count':
        return len(vals)
    nums = []
    for v in vals:
        try:
            nums.append(float(v))
        except (ValueError, TypeError):
            continue
    if fn == 'sum':
        return sum(nums)
    if not nums:
        return 0
    if fn == 'avg':
        return sum(nums) / len(nums)
    if fn == 'min':
        return min(nums)
    return max(nums)


def _parse_totals(raw, where):
    """Normaliza totals -> {label, align, span} | None. Ausente = não totaliza."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: totals deve ser dict")
    for k in raw:
        if k not in ('label', 'align', 'span'):
            raise ValueError(f"{where}: chave '{k}' inválida em totals")
    align = raw.get('align', 'C')
    if align not in ('L', 'C', 'R'):
        raise ValueError(f"{where}: align deve ser L|C|R")
    span = raw.get('span', 1)
    if isinstance(span, bool) or not isinstance(span, int) or span < 1:
        raise ValueError(f"{where}: span deve ser int >= 1")
    return {'label': raw.get('label', TOTALS_DEFAULT_LABEL),
            'align': align, 'span': span}


@dataclass
class _ReportTable:
    """Tabela do relatório (interno de renderização)."""
    columns: ReportColumns = None
    totals: Optional[dict] = None
    after: Optional[object] = None
    rows_before: int = 0
    rows_after: int = 0


@dataclass
class _ReportFooter:
    """Rodapé de página (interno de renderização)."""
    text: Optional[object] = None
    show_user: bool = False
    show_datetime: bool = False
    show_company: bool = False
    show_page_number: bool = False
    separator: str = ' | '
    align: str = 'C'
    font_size: int = 8


def _build_header(report: Report) -> '_ReportHeader':
    if isinstance(report.header, list):
        # Forma lista: header=[...] (ReportItem). Defaults + raw p/ render.
        return _ReportHeader(
            show_logo=False,
            logo_path=report.logo_path,
            title_font_size=_HEADER_DEFAULTS['title'].get('font_size', 16),
            title_font_style=_HEADER_DEFAULTS['title'].get('font_style', 'B'),
            title_align=_HEADER_DEFAULTS['title'].get('align', 'C'),
            subtitle_font_size=10,
            subtitle_align='C',
            raw_header=list(report.header),
        )
    h = {**_HEADER_DEFAULTS, **(report.header or {})}

    # Logo: location (caixa em grade ou [âncora, linhas]) ou legado position.
    # Shim: position traduzido p/ location; os dois juntos = fail-fast.
    logo_cfg = {**_HEADER_DEFAULTS.get('logo', {}), **(h.get('logo') or {})}
    logo_location = logo_cfg.get('location')
    _declared = h.get('logo') or {}
    if logo_location is not None and 'position' in _declared:
        raise ValueError("header.logo: use location ou position (não ambos)")
    if logo_location is None and _declared.get('position', 'N') != 'N':
        pos = _declared.get('position')
        if pos not in ('C', 'L', 'R'):
            raise ValueError(f"header.logo: position '{pos}' desconhecida (use location)")
        logo_location = [pos, _declared.get('lines', logo_cfg.get('lines', 4))]
    show_logo = logo_location is not None
    logo_align = 'C'

    # Título: dict (deep merge) ou str
    t_raw = h.get('title')
    title_cfg = {**_HEADER_DEFAULTS.get('title', {}),
                 **(t_raw if isinstance(t_raw, dict) else {})}
    title = (title_cfg.get('label') if isinstance(t_raw, dict) else None) \
        or (t_raw if isinstance(t_raw, str) else None) \
        or report.label
    title_font_size = title_cfg.get('font_size', h.get('title_font_size', 16))
    title_font_style = title_cfg.get('font_style', h.get('title_font_style', 'B'))
    title_align = title_cfg.get('align', h.get('title_align', 'C'))

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
        logo_height=0,
        logo_align=logo_align,
        logo_location=logo_location,
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
        line=bool(h.get('line', False)),
    )


def _render_header_items(self, h):
    """Header em forma lista: LOGO/TITLE (cascata)/FIELD/TEXT/IMAGE/formas."""
    from ajsystem.defs.report import parse_report_item
    from ajsystem.core.text import render as _trender
    label = self._report.label if getattr(self, '_report', None) else ''
    items = [parse_report_item(it, label) for it in (h.raw_header or [])]
    self._tabs = None
    titles = 0
    for item in items:
        cfg = item.config
        if item.kind == 'TABS':
            _raw = cfg if isinstance(cfg, list) else cfg.get('values', [])
            _stops = [_eval_tab_value(self, _s, label) for _s in _raw]
            if sorted(_stops) != list(_stops):
                raise ValueError(f"report '{label}': TABS deve vir em ordem crescente")
            self._tabs = list(_stops)
            continue
        if item.kind == 'POS':
            _vals = cfg if isinstance(cfg, list) else cfg.get('values', [])
            if len(list(_vals)) != 2:
                raise ValueError(f"report '{label}': POS exige [col, lin]")
            self.set_font(FONT_FAMILY, "", FONT_CELL)
            _c, _r = _resolve_tokens(self, list(_vals), label)
            for _v in (_c, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)):
                    raise ValueError(f"report '{label}': POS exige [col, lin]")
            self.set_xy(self.l_margin + _c * (self.get_string_width('0') or 2.0),
                        self.t_margin + _r * ROW_CELL)
            continue
        if item.kind == 'LOGO':
            logo = h.logo_path
            if not logo:
                continue
            loc = cfg.get('location', ['C', 4])
            x, y, w, hh = _image_box(self, loc, logo)
            self.image(logo, x=x, y=y, w=w, h=hh)
            # Cursor p/ o fim da caixa (PCOL = fim do logo): o próximo item
            # ancora a partir daqui; sem âncora, o bloco volta à margem.
            self.set_xy(x + w, y + hh)
        elif item.kind == 'TITLE':
            if cfg.get('when') is not None:
                from ajsystem.core.text import eval_when as _ew
                if not _ew(self._instance, cfg['when']):
                    continue
            titles += 1
            first = titles == 1
            txt = cfg.get('text', cfg.get('label', label))
            if 'tab' in cfg:
                if any(k in cfg for k in ('location', 'pos')):
                    raise ValueError(f"report '{label}': tab não combina com location/pos")
                _tab_x(self, cfg['tab'], label)
            elif any(k in cfg for k in ('location', 'pos')):
                _anchor(self, cfg, label)
            else:
                self.set_x(self.l_margin)  # bloco: volta à margem, Y flui
            if callable(txt) and self._instance:
                txt = txt(self._instance)
            elif self._instance and isinstance(txt, str) and '{id}' in txt:
                txt = txt.replace('{id}', str(getattr(self._instance, 'id', '')))
            if hasattr(self, '_title_substitutions'):
                for k, v in self._title_substitutions.items():
                    txt = (txt or '').replace('{' + k + '}', str(v))
            size = h.title_font_size if first else h.subtitle_font_size
            style = h.title_font_style if first else ''
            # TITLE sempre centralizado por default; outro align só se declarado.
            align = cfg.get('align', 'C')
            self.set_font(FONT_FAMILY, style, size)
            _w = cfg.get('width')
            if _w is not None:
                if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
                    raise ValueError(f"report '{label}': width deve ser cols > 0")
                self.set_font(FONT_FAMILY, "", FONT_CELL)
                _w = _w * (self.get_string_width('0') or 2.0)
                self.set_font(FONT_FAMILY, style, size)
            else:
                _w = 0  # coluna corrente até o fim da linha
            self.cell(_w, size * 0.6, txt or '', align=align, new_x="LMARGIN", new_y="NEXT")
            self.ln(GAP_TITLE if first else GAP_SUBTITLE)
        elif item.kind == 'FIELD':
            if self._instance is None:
                continue  # sem instância: omite (legado do cabeçalho)
            if cfg.get('when') is not None:
                from ajsystem.core.text import eval_when as _ew
                if not _ew(self._instance, cfg['when']):
                    continue
            _render_items(self, [{'field': item.name, **cfg}], self._instance, self._report,
                          reset_tabs=False)
        else:
            _render_items(self, [{item.kind: cfg}], self._instance, self._report,
                          reset_tabs=False)


def _report_body(report):
    """Conteúdo do `Report.body` (ReportBody) — {} se ausente."""
    return report.body if report else None


def _body_table(report):
    """Dict `table` do corpo (fonte de columns/hierarchy)."""
    body = _report_body(report)
    return (getattr(body, 'table', None) or {}) if body else {}


def _build_table(report: Report) -> '_ReportTable':
    t = _body_table(report)
    columns = t.get('columns')
    if isinstance(columns, dict):
        columns = ReportColumns(columns)
    for _c in (list(columns) if columns else []):
        if _c.agg is not None and _c.agg not in TOTALS_FUNCS:
            raise ValueError(f"coluna '{_c.field}': agg '{_c.agg}' deve ser {list(TOTALS_FUNCS)}")
    totals = _parse_totals(t.get('totals'), 'table.totals')
    if totals is None and (t.get('footer') or any(getattr(_c, 'agg', None) for _c in (list(columns) if columns else []))):
        # Shim legado: footer:true + agg nas colunas -> totals (span legado).
        totals = {'label': t.get('footer_label', TOTALS_DEFAULT_LABEL),
                  'align': 'R', 'span': None}
    return _ReportTable(
        columns=columns,
        totals=totals,
        after=t.get('after'),
        rows_before=t.get('rows_before', 0),
        rows_after=t.get('rows_after', 0),
    )


def _build_footer(report: Report) -> '_ReportFooter':
    f = report.footer or {}
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


class DocPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(FOOTER_Y)
        self.set_font(FONT_FAMILY, "I", FONT_FOOTER)
        self.cell(0, LINE_TALL, f"Página {self.page_no()}/{{nb}}", align="C")


def _fmt(val):
    """Format numeric value as BRL string with thousands separator."""
    if val is None:
        return "R$ 0,00"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# Report-based PDF generation
# ---------------------------------------------------------------------------

class DocPDFReport(FPDF):
    """FPDF subclass that renders header/footer from a Report config."""

    def __init__(self, report: Report, **kwargs):
        page_size = report.page_size
        orientation = report.orientation
        super().__init__(orientation=orientation, format=page_size, **kwargs)
        self._report = report
        self._header = _build_header(report)
        self._footer_cfg = _build_footer(report)
        self._is_first_page = True
        self._instance = None
        # Metadados: título = label do Report (nome exibido pelo viewer;
        # sem isso, data URI vira o "nome" do documento no canto esquerdo)
        self.set_title(report.label)
        self.alias_nb_pages()

    def set_instance(self, instance):
        self._instance = instance

    def header(self):
        h = self._header
        if not self._is_first_page and not h.on_each_page:
            return
        self._is_first_page = False

        # Forma lista (header=[...]): itens em ordem; dict legado abaixo.
        if isinstance(h.raw_header, list):
            _render_header_items(self, h)
            if h.line:
                y = self.get_y()
                self.line(self.l_margin, y, self.w - self.r_margin, y)
            return

        # Resolver logo_width
        logo_w = h.logo_width
        if logo_w is None:
            logo_w = self.w * 0.25 if h.layout == 'logo_left' else 60

        if h.layout == 'logo_left':
            self._render_header_logo_left(h, logo_w)
        else:
            # Logo via location (caixa em grade ou [âncora, linhas])
            if h.show_logo and h.logo_location is not None:
                logo = h.logo_path
                if logo:
                    x, y, w, hh = _image_box(self, h.logo_location, logo)
                    self.image(logo, x=x, y=y, w=w, h=hh)
                    self.set_y(y + hh)
            self._render_header_centered(h)

        if h.line:
            y = self.get_y()
            self.line(self.l_margin, y, self.w - self.r_margin, y)

    def _render_header_logo_left(self, h, logo_w):
        """Renderiza header com logo à esquerda, título + campos à direita."""
        padding = 4
        right_x = self.l_margin + logo_w + padding
        right_w = self.w - self.r_margin - right_x
        y0 = self.get_y()

        # Logo: alinhar topo com primeiro campo
        logo_y = y0
        self.image(h.logo_path, x=self.l_margin, y=logo_y, w=logo_w, h=0)
        logo_bottom = logo_y + logo_w * 0.55

        # Título centralizado na área direita
        if h.title:
            title = h.title
            if callable(title) and self._instance:
                title = title(self._instance)
            elif self._instance and '{id}' in title:
                title = title.replace('{id}', str(getattr(self._instance, 'id', '')))
            self.set_xy(right_x, y0)
            self.set_font(FONT_FAMILY, h.title_font_style, h.title_font_size)
            self.cell(right_w, h.title_font_size * 0.6, title, align='C',
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(GAP_TITLE_SIDE)

        # Campos do header na área direita
        if h.fields and self._instance:
            self._render_header_fields(h.fields, h.field_columns,
                                       x_start=right_x, area_width=right_w)

        # Avançar Y além do logo se necessário
        self.set_y(max(self.get_y(), logo_bottom) + 4)

    def _render_header_centered(self, h):
        """Renderiza header centralizado (layout padrão)."""
        # Title
        if h.title:
            title = h.title
            if callable(title) and self._instance:
                title = title(self._instance)
            elif self._instance and '{id}' in title:
                title = title.replace('{id}', str(getattr(self._instance, 'id', '')))
            if hasattr(self, '_title_substitutions'):
                for k, v in self._title_substitutions.items():
                    title = title.replace('{' + k + '}', str(v))
            self.set_font(FONT_FAMILY, h.title_font_style, h.title_font_size)
            self.cell(0, h.title_font_size * 0.6, title, align=h.title_align,
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(GAP_TITLE)

        # Subtitle
        if h.subtitle:
            self.set_font(FONT_FAMILY, "", h.subtitle_font_size)
            self.cell(0, h.subtitle_font_size * 0.5, h.subtitle,
                      align=h.subtitle_align, new_x="LMARGIN", new_y="NEXT")
            self.ln(GAP_SUBTITLE)

        # Header fields
        if h.fields and self._instance:
            self._render_header_fields(h.fields, h.field_columns)

        if not h.on_each_page:
            self.ln(GAP_HEAD_FIELDS_SINGLE)

    def _render_header_fields(self, fields, num_columns, x_start=None, area_width=None):
        parsed = [parse_header_field(f) for f in fields]
        if x_start is None:
            x_start = self.l_margin
        if area_width is None:
            area_width = self.w - self.l_margin - self.r_margin
        col_w = area_width / num_columns
        y0 = self.get_y()
        row_h = ROW_CELL
        col = 0
        row = 0
        for rf in parsed:
            x = x_start + col * col_w
            y = y0 + row * row_h
            # Label (bold)
            self.set_xy(x, y)
            self.set_font(FONT_FAMILY, "B", FONT_FIELD)
            lbl = (rf.label or rf.field or '') + ':'
            self.cell(col_w * 0.4, row_h, lbl, new_x="END")
            # Value
            self.set_font(FONT_FAMILY, "", FONT_FIELD)
            val = self._get_field_value(rf)
            align = 'R' if rf.align == 'right' else 'L'
            self.cell(col_w * 0.6, row_h, val, align=align, new_x="END")
            col += 1
            if col >= num_columns:
                col = 0
                row += 1
        self.set_y(y0 + (row + (1 if col > 0 else 0)) * row_h + GAP_HEAD_FIELDS)

    def _get_field_value(self, rf: ReportField) -> str:
        val = None
        if rf.function and self._instance:
            try:
                val = rf.function(self._instance)
            except Exception:
                val = '-'
        elif rf.field and self._instance:
            val = getattr(self._instance, rf.field, None)
        if val is None:
            return '-'
        if rf.format == 'brl':
            return _fmt(val)
        if rf.format is True or isinstance(rf.format, int):
            return fmt_money(val, rf.format)
        if rf.format == 'date' and hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y')
        if rf.format == 'datetime' and hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y %H:%M')
        if _is_mask(rf.format):
            from ajsystem.core.formats import fmt_mask as _fm
            try:
                return _fm(val, rf.format)
            except Exception:
                return str(val)
        return str(val)

    def footer(self):
        f = self._footer_cfg
        parts = []
        if f.text:
            txt = f.text
            if callable(txt):
                try:
                    txt = txt(self._instance) if self._instance else ''
                except Exception:
                    txt = ''
            else:
                # Substituir placeholders
                user_name = ''
                try:
                    user_name = current_user.username if current_user.is_authenticated else ''
                except Exception:
                    pass
                txt = txt.replace('{user}', user_name)
                txt = txt.replace('{datetime}', datetime.now().strftime('%d/%m/%Y %H:%M'))
                txt = txt.replace('{company}', '')
                txt = txt.replace('{page}', str(self.page_no()))
                txt = txt.replace('{total}', '{nb}')
            if txt:
                parts.append(txt)
        if f.show_user:
            try:
                user_name = current_user.username if current_user.is_authenticated else ''
            except Exception:
                user_name = ''
            if user_name:
                parts.append(user_name.upper())
        if f.show_datetime:
            parts.append(datetime.now().strftime('%d/%m/%Y %H:%M'))
        if f.show_company:
            parts.append('')
        if f.show_page_number:
            parts.append(f"Página {self.page_no()}/{{nb}}")
        if parts:
            self.set_y(FOOTER_Y)
            self.set_font(FONT_FAMILY, "I", f.font_size)
            self.cell(0, LINE_TALL, f.separator.join(parts), align=f.align)


def _get_cell_value(row, col: ReportColumn):
    """Obtém valor de uma coluna para uma linha de dados."""
    if col.function:
        try:
            val = col.function(row)
        except Exception:
            val = None
    elif col.field:
        parts = col.field.split('.')
        val = row
        for p in parts:
            if val is None:
                break
            val = getattr(val, p, None)
    else:
        val = None
    return val


def _is_mask(fmt) -> bool:
    """fmt parece máscara (dígitos 9, tokens de data ou alfa)?"""
    if not isinstance(fmt, str):
        return False
    if '9' in fmt:
        return True
    from ajsystem.core.formats import has_date_tokens as _hdt, _ALPHA_TOKEN_RE as _are
    try:
        return bool(_hdt(fmt) or _are.search(fmt))
    except Exception:
        return False


def _format_cell_value(val, fmt: str) -> str:
    """Formata valor para exibição na célula.

    fmt máscara (Entity, ex. '(99) 99999-9999', 'dd/mm/yyyy ddd') formata
    via máscara — igual à list; demais literais caem no str().
    """
    if val is None:
        return '-'
    if fmt == 'brl':
        return _fmt(val)
    if fmt is True or isinstance(fmt, int):
        return fmt_money(val, fmt)
    if fmt == 'date' and hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y')
    if fmt == 'datetime' and hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y %H:%M')
    if _is_mask(fmt):
        from ajsystem.core.formats import fmt_mask as _fm
        try:
            return _fm(val, fmt)
        except Exception:
            return str(val)
    if fmt == 'int':
        try:
            return str(int(val))
        except (ValueError, TypeError):
            return str(val)
    if fmt == 'float':
        try:
            return f"{float(val):,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return str(val)
    return str(val)


MIN_COL_WIDTH = 15  # mm

_MISSING = object()  # sentinela p/ suppress (None é valor válido de comparar)

# ── Medidas fixas do motor (valores idênticos aos literais anteriores) ──────
# Centralizadas aqui para não espalhar mágicos; viram props de relatório só
# com aprovação (ver conversa). Nada abaixo muda comportamento.
FONT_FAMILY = "Helvetica"
FONT_TITLE = 16        # título do cabeçalho
FONT_SUBTITLE = 10     # subtítulo
FONT_FIELD = 9         # fields do cabeçalho (label e valor)
FONT_HEAD = 9          # cabeçalho das colunas
FONT_CELL = 9          # célula de dados
FONT_FOOT = 9          # linha de total
FONT_GROUP_TITLE = 11  # título de grupo (pos 2)
FONT_GROUP_TITLE_SMALL = 10  # título fora de pos 2 (defensivo)
FONT_GROUP_LINE = 9    # linha de grupo (pos 1)
FONT_ITEMS = 10        # itens inline (field/text)
FONT_FOOTER = 8        # rodapé de página
ROW_HEAD = 7           # altura linha de cabeçalho das colunas
ROW_CELL = 6           # altura linha de dados / unidade de grade e de rows_*
ROW_FOOT = 7           # altura linha de total
ROW_GROUP_TITLE = 8    # altura título de grupo
ROW_GROUP_LINE = 7     # altura linha de grupo
GAP_TITLE = 4          # após título
GAP_SUBTITLE = 3       # após subtítulo
GAP_HEAD_FIELDS = 4    # após fields do cabeçalho
GAP_TEXT_LINE = 2      # antes de cada linha avulsa
GAP_TEXT_EMPTY = 8     # linha avulsa vazia
GAP_HEAD_FIELDS_SINGLE = 4  # após fields quando cabeçalho é só da 1ª página
INDENT_GROUP_TITLE = 2   # recuo título de grupo (mm)
INDENT_GROUP_LINE = 6    # recuo linha de grupo (mm)
INDENT_PER_LEVEL = 4     # recuo adicional por nível (mm)
FOOTER_Y = -15           # recuo do rodapé de página
LINE_TALL = 10           # altura de linha avulsa larga (rodapé, erro)
GAP_TITLE_SIDE = 2      # após título no layout logo_left
GAP_AFTER_TABLE = 4     # antes do texto after da tabela
GAP_TEXTS = 4           # antes de cada texto avulso


def _calc_col_widths(pdf, cols):
    """Converte widths (ch) → mm pela métrica da fonte e distribui.

    - Colunas com `width` (ch) → mm exato via largura do glifo '0';
    - Sem nenhuma width → divisão igual;
    - Com widths parciais → restante dividido entre as sem width;
    - Todas com width → bloco centrado no disponível.
    """
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    unit = pdf.get_string_width('0') or 2.0
    n = len(cols)
    conv = [(c.width or 0) * unit for c in cols]
    if not any(c.width for c in cols):
        col_widths = [avail_w / n] * n
    else:
        leftover = max(avail_w - sum(conv), 0.0)
        missing = [i for i, c in enumerate(cols) if not c.width]
        if missing:
            share = leftover / len(missing)
            for i in missing:
                conv[i] = share
        col_widths = conv
    total_w = sum(col_widths)
    x_start = pdf.l_margin + (avail_w - total_w) / 2
    return col_widths, total_w, x_start


def _check_page_break(pdf, needed_h):
    """Verifica se há espaço. Se não, fecha tabela e adiciona página."""
    if pdf.get_y() + needed_h + pdf.b_margin <= pdf.h:
        return False
    pdf.add_page()
    return True


def _draw_hline(pdf, x_start, total_w):
    """Desenha linha horizontal (sem laterais)."""
    y = pdf.get_y()
    pdf.line(x_start, y, x_start + total_w, y)


def _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=True):
    """Renderiza cabeçalhos das colunas com linhas horizontais."""
    if draw_top_line:
        _draw_hline(pdf, x_start, total_w)
    pdf.set_font(FONT_FAMILY, "B", FONT_HEAD)
    row_h = ROW_HEAD
    for i, col in enumerate(cols):
        align = 'C' if col.align == 'center' else ('R' if col.align == 'right' else 'L')
        nx = "LMARGIN" if i == len(cols) - 1 else "END"
        ny = "NEXT" if i == len(cols) - 1 else "TOP"
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], row_h, col.label or col.field, border=0, align=align, new_x=nx, new_y=ny)
    _draw_hline(pdf, x_start, total_w)


def _render_data_row(pdf, cols, col_widths, row, x_start, agg_values):
    """Renderiza uma linha de dados."""
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)
    row_h = ROW_CELL
    if not hasattr(pdf, '_sup_prev'):
        pdf._sup_prev = {}
    for i, col in enumerate(cols):
        val = _get_cell_value(row, col)
        _blank = False
        if getattr(col, 'suppress', False):
            if pdf._sup_prev.get(col.field, _MISSING) == val:
                _blank = True
            else:
                pdf._sup_prev[col.field] = val
        txt = '' if _blank else _format_cell_value(val, col.format)
        align = 'R' if col.align == 'right' else ('C' if col.align == 'center' else 'L')
        nx = "LMARGIN" if i == len(cols) - 1 else "END"
        ny = "NEXT" if i == len(cols) - 1 else "TOP"
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], row_h, txt, border=0, align=align, new_x=nx, new_y=ny)
        if col.agg and val is not None:
            agg_values[col.field].append(val)
    if pdf._report.show_table_lines:
        _draw_hline(pdf, x_start, sum(col_widths))


def _render_footer_row(pdf, cols, col_widths, totals, agg_values, x_start, total_w):
    """Linha de total geral: rótulo nas SPAN primeiras + func por coluna agg."""
    pdf.set_font(FONT_FAMILY, "B", FONT_FOOT)
    span = totals.get('span')
    nspan = len(cols) - 1 if span is None else min(span, len(cols) - 1)
    label_w = sum(col_widths[:nspan])
    pdf.set_x(x_start)
    pdf.cell(label_w, ROW_FOOT, totals.get('label', TOTALS_DEFAULT_LABEL),
             border=0, align=totals.get('align', 'C'))
    _positions = [i for i, col in enumerate(cols) if i >= nspan and col.agg]
    if not _positions:
        pdf.set_x(x_start + label_w)
        pdf.cell(total_w - label_w, ROW_FOOT, '', border=0,
                 new_x="LMARGIN", new_y="NEXT")
    for i in _positions:
        col = cols[i]
        v = _agg_apply(col.agg, agg_values.get(col.field))
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], ROW_FOOT, _format_cell_value(v, col.format),
                 border=0, align="R",
                 **({'new_x': "LMARGIN", 'new_y': "NEXT"} if i == _positions[-1] else {}))
    _draw_hline(pdf, x_start, total_w)


def _table_close(pdf, x_start, total_w):
    """Linha de fechamento da tabela."""
    _draw_hline(pdf, x_start, total_w)


def _group_value(row, g):
    v = getattr(row, g['field'], None)
    if v is None and g.get('function'):
        v = g['function'](row)
    if g.get('left'):
        # left(n) = n primeiros SEGMENTOS do código ('1.2.01'/2 → '1.2')
        sc = g.get('sep', '.')
        v = sep_join(str(v or ''), g['left'], sc)
    elif g.get('anchor_self') and v is None:
        # raiz âncora: pai nulo usa o próprio id (abre e pertence ao bloco)
        v = getattr(row, 'id', None)
    return v


def sep_join(code, n, sep='.'):
    parts = code.split(sep)
    return sep.join(parts[:n])


def _group_title(g, val, row=None):
    """Título do grupo — template `text` (avaliador único core/text).

    '{campo}' = label da Entity (LIST → options); '{campo:spec}' = valor cru;
    '{?campo:literal}' = segmento condicional; `{<g.field>}` = valor do grupo.
    Ex.: '{tipo:d}. {tipo}' → '1. Receitas'. Sem `text` → str(valor).
    """
    from ajsystem.core.text import render as _render
    tpl = g.get('text')
    if not tpl:
        return apply_transform(str(val or ''), g.get('transform'))
    fmt_opts = g.get('_fmt_opts') or {}

    def _get(name):
        if name == g.get('field'):
            return val
        if row is None:
            return None
        from ajsystem.core.text import dotted_get as _dg
        return _dg(row, name)

    return apply_transform(_render(tpl, _get, fmt_opts), g.get('transform'))


def _render_group_header(pdf, g, val, xs, tw, pos, row=None):
    txt = apply_transform(_group_title(g, val, row=row), g.get('transform'))
    style = 'B' if g.get('bold', True) else ''
    size = FONT_GROUP_TITLE if pos == 2 else FONT_GROUP_TITLE_SMALL
    indent = INDENT_GROUP_TITLE if pos == 2 else INDENT_GROUP_LINE
    height = ROW_GROUP_TITLE if pos == 2 else ROW_GROUP_LINE
    pdf.set_font(FONT_FAMILY, style, size)
    pdf.set_x(xs + indent)
    pdf.cell(tw - indent, height, txt, border=0,
             new_x="LMARGIN", new_y="NEXT")


def _render_group_line(pdf, g, val, xs, tw, row=None):
    """Linha `pos=1` — interna à tabela, texto corrido na largura da tabela."""
    txt = apply_transform(_group_title(g, val, row=row), g.get('transform'))
    style = 'B' if g.get('bold', True) else ''
    pdf.set_font(FONT_FAMILY, style, FONT_GROUP_LINE)
    indent = max(1, int(g.get('left', 1) or 1)) * INDENT_PER_LEVEL
    height = ROW_GROUP_LINE
    pdf.set_x(xs + indent)
    pdf.cell(tw - indent, height, txt, border=0,
             new_x="LMARGIN", new_y="NEXT")


def _render_group_total(pdf, g, cols, cw, xs, acc, row=None):
    """Subtotal do grupo. totals ausente = não totaliza (legado total:True +
    footer_text traduzido)."""
    totals = _parse_totals(g.get('totals'), 'groups.totals')
    if totals is None:
        if g.get('total', True):
            totals = {'label': g.get('footer_text') or 'Sub-Total',
                      'align': 'R', 'span': None}
        else:
            return
    if not any(c.agg for c in cols):
        return
    pdf.set_font(FONT_FAMILY, "B", FONT_FOOT)
    label = totals.get('label', 'Sub-Total')
    if label and row is not None and ('{' in label):
        label = _group_title({**g, 'text': label}, None, row=row)
    span = totals.get('span')
    nspan = len(cols) - 1 if span is None else min(span, len(cols) - 1)
    label_w = sum(cw[:nspan])
    pdf.set_x(xs)
    pdf.cell(label_w, ROW_FOOT, label, border=0, align=totals.get('align', 'C'))
    _positions = [i for i, col in enumerate(cols) if i >= nspan and col.agg]
    if not _positions:
        pdf.set_x(xs + label_w)
        pdf.cell(sum(cw[nspan:]), ROW_FOOT, '', border=0,
                 new_x="LMARGIN", new_y="NEXT")
        return
    for i in _positions:
        col = cols[i]
        v = _agg_apply(col.agg, acc.get(col.field))
        pdf.set_x(xs + sum(cw[:i]))
        pdf.cell(cw[i], ROW_FOOT, _format_cell_value(v, col.format),
                 border=0, align="R",
                 **({'new_x': "LMARGIN", 'new_y': "NEXT"} if i == _positions[-1] else {}))


def _walk_field_groups(pdf, cols, cw, tw, xs, data, gs,
                       agg_values, header_h, report):
    """Grupos por mudança de valor do campo (specs normalizadas)."""
    lines_after = (_body_table(report)).get('rows_after', 0) if report else 0
    show_lines = bool(report.show_table_lines) if report else False
    prev = [None] * len(gs)
    accs = [{c.field: [] for c in cols if c.agg} for _ in gs]
    last_rows = [None] * len(gs)
    started = False
    table_open = False   # nada foi desenhado ainda — evita fechar tabela fantasma
    gera_cab = True

    def close_level(i):
        g = gs[i]
        if not started:
            return
        if g.get('totals') is not None or g.get('total', True):
            _render_group_total(pdf, g, cols, cw, xs, accs[i],
                                row=last_rows[i])
        if g.get('line', True):
            _draw_hline(pdf, xs, tw)

    for row in data:
        vals = [_group_value(row, g) for g in gs]
        changed = 0 if not started else \
            next((i for i in range(len(gs)) if vals[i] != prev[i]), None)

        opened_linha = False
        skip_row = False
        if changed is not None:
            # fecha do nível mais interno até o primeiro alterado
            for i in range(len(gs) - 1, changed - 1, -1):
                close_level(i)
            # abre níveis alterados (e internos herdam abertura)
            for i in range(changed, len(gs)):
                g = gs[i]
                if g.get('eject'):
                    pdf.add_page()
                pos = g['pos']
                if pos == 2:                     # titulo
                    if table_open:
                        _table_close(pdf, xs, tw)
                        table_open = False
                    if lines_after:
                        pdf.ln(lines_after * ROW_CELL)
                    _render_group_header(pdf, g, vals[i], xs, tw, pos, row)
                    gera_cab = True
                elif pos == 1:                   # linha — interna a tabela, texto único
                    if not table_open:
                        table_open = True
                    pb = _check_page_break(pdf, header_h)
                    if gera_cab or pb:
                        _render_column_headers(pdf, cols, cw, xs, tw,
                                               draw_top_line=True)
                        gera_cab = False
                    _render_group_line(pdf, g, vals[i], xs, tw, row)
                    # a row que ABRE o nível é a própria linha (consumida como
                    # cabeçalho), não repete como dado na tabela
                    skip_row = True
                # pos == 0: oculto — agrupa/totaliza sem imprimir cabeçalho
                prev[i] = vals[i]
                last_rows[i] = row
            started = True
            for i in range(len(gs)):
                last_rows[i] = row

        if skip_row:
            continue

        if not table_open:
            table_open = True
        page_break = _check_page_break(pdf, header_h)
        if gera_cab or page_break:
            _render_column_headers(pdf, cols, cw, xs, tw, draw_top_line=True)
            gera_cab = False
        if show_lines:
            _draw_hline(pdf, xs, tw)
        _render_data_row(pdf, cols, cw, row, xs, agg_values)
        for acc in accs:
            for c in cols:
                if c.agg:
                    v = _get_cell_value(row, c)
                    if v is None and not c.function:
                        v = getattr(row, c.field, None)
                    acc[c.field].append(v)

    # fecha grupos remanescentes
    for i in range(len(gs) - 1, -1, -1):
        close_level(i)
    if show_lines:
        _draw_hline(pdf, xs, tw)


def _render_table(pdf: DocPDFReport, columns: ReportColumns,
                  data: list, totals: Optional[dict] = None,
                  instance=None, draw_top_line=True, report=None):
    """Renderiza uma tabela no PDF com centralização, sem laterais,
    page break com repetição de cabeçalho e shrink-to-fit."""
    cols = list(columns)
    if not cols:
        return
    pdf._sup_prev = {}

    col_widths, total_w, x_start = _calc_col_widths(pdf, cols)

    # Verificar largura mínima
    for i, col in enumerate(cols):
        if col_widths[i] < MIN_COL_WIDTH:
            pdf.set_font(FONT_FAMILY, "B", FONT_ITEMS)
            pdf.cell(0, LINE_TALL, f"Erro: coluna '{col.label or col.field}' muito estreita "
                     f"({col_widths[i]:.1f}mm < {MIN_COL_WIDTH}mm). "
                     f"Largura insuficiente para o relatório.",
                     align="C", new_x="LMARGIN", new_y="NEXT")
            return

    # Dados — grupos por mudança de valor (specs normalizadas em _apply_entity)
    agg_values = {c.field: [] for c in cols if c.agg}
    header_h = ROW_HEAD + ROW_CELL
    gera_cab = True
    gs = [g for g in (_body_table(report).get('levels', _body_table(report).get('hierarchy', [])))
          if isinstance(g, dict) and 'field' in g] \
        if report else []

    if gs:
        _walk_field_groups(pdf, cols, col_widths, total_w, x_start, data,
                           gs, agg_values, header_h, report)
    else:
        for row in data:
            page_break = _check_page_break(pdf, header_h)
            if gera_cab or page_break:
                _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=True)
                gera_cab = False
            _render_data_row(pdf, cols, col_widths, row, x_start, agg_values)

    # Linha de fechamento da tabela
    if totals is None:
        _table_close(pdf, x_start, total_w)

    # Linha de total geral — com sua própria linha de fechamento
    if totals is not None:
        footer_h = ROW_FOOT
        if _check_page_break(pdf, footer_h):
            _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
        _render_footer_row(pdf, cols, col_widths, totals, agg_values, x_start, total_w)


def _render_table_lines(pdf, lines, instance=None):
    """Renderiza lista de linhas (before_table / after_table)."""
    for line in lines or []:
        text = line.get('text', '')
        if callable(text) and instance:
            text = text(instance)
        text = text or ''
        size = line.get('font_size', 10)
        style = line.get('font_style', '')
        align = line.get('align', 'L')
        w = line.get('width', 0)
        if not text and w == 0:
            pdf.ln(GAP_TEXT_EMPTY)
            continue
        pdf.ln(GAP_TEXT_LINE)
        pdf.set_font(FONT_FAMILY, style, size)
        pdf.cell(w, size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")





def _split_item(it, label):
    """Normaliza 1 item de body.items -> (kind, name, cfg).

    str = FIELD; minúscula ({alias: cfg} ou {field: ...}) = FIELD;
    MAIÚSCULA (TEXT/IMAGE/LINE/BOX/CIRCLE/LOGO/TITLE/TABS/POS) = elemento.
    TABS/POS exigem lista; demais elementos exigem dict. fail-fast.
    """
    if isinstance(it, str):
        return ('FIELD', it, {})
    if callable(it):
        return ('CALL', getattr(it, '__name__', 'call'), {'fn': it})
    if isinstance(it, dict):
        if 'field' in it:
            return ('FIELD', it.get('field'), {k: v for k, v in it.items() if k != 'field'})
        if len(it) == 1:
            (k, v), = it.items()
            if k.isupper():
                from ajsystem.defs.report import ITEM_KINDS as _KINDS
                if k not in _KINDS:
                    raise ValueError(f"report '{label}': elemento '{k}' desconhecido")
                if k in ('TABS', 'POS'):
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': '{k}' exige lista")
                    return (k, k, {'values': v})
                if k == 'FIELDS':
                    if not isinstance(v, dict):
                        raise ValueError(f"report '{label}': 'FIELDS' exige dict")
                    return (k, k, v)
                if not isinstance(v, dict):
                    raise ValueError(f"report '{label}': '{k}' exige dict de props")
                return (k, k, v)
            return ('FIELD', k, v if isinstance(v, dict) else {})
    raise ValueError(f"report '{label}': item deve ser str ou dict, veio {it!r}")


def _image_box(pdf, location, path):
    """Caixa absoluta (x, y, w, h mm) de IMAGE/logo: caixa em grade ou
    [âncora, linhas] (altura em linhas, largura pela proporção real via PIL).
    Origem = área útil.
    """
    from PIL import Image as _PIL
    from ajsystem.core.geom import normalize as _gloc, resolve_anchor as _ra, to_mm as _gmm
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)  # get_string_width exige fonte; ref fixa
    col_w = pdf.get_string_width('0') or 2.0
    norm = _gloc('IMAGE', location)
    if norm[0] == 'IMAGE_ANCHOR':
        _, anchor, lines = norm
        iw, ih = _PIL.open(path).size
        area_cols = (pdf.w - pdf.l_margin - pdf.r_margin) / col_w
        norm = _gloc('IMAGE', _ra(anchor, lines, iw, ih, ROW_CELL, col_w, area_cols))
    g = _gmm(norm, ROW_CELL, col_w)
    return pdf.l_margin + g['x'], pdf.t_margin + g['y'], g['w'], g['h']


def _grid_pos(pdf):
    """Cursor corrente em grade (PCOL, PROW)."""
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)  # referência fixa da grade
    col_w = pdf.get_string_width('0') or 2.0
    return ((pdf.get_x() - pdf.l_margin) / col_w,
            (pdf.get_y() - pdf.t_margin) / ROW_CELL, col_w)


def _resolve_tokens(pdf, values, label):
    """Troca PROW/PCOL (literal ou constante) pela posição corrente. Só âncora
    (2 termos); em extensão (w/h/c2/r2/deltas) ou fora de lista = fail-fast."""
    from ajsystem.defs.report import _CursorExpr as _CE
    out = []
    for v in values:
        if isinstance(v, _CE):
            if v.base not in ('PCOL', 'PROW'):
                raise ValueError(f"report '{label}': cursor '{v.base}' desconhecido")
            out.append(_grid_pos(pdf)[0 if v.base == 'PCOL' else 1] + v.offset)
            continue
        if v == 'PROW':
            out.append(_grid_pos(pdf)[1])
        elif v == 'PCOL':
            out.append(_grid_pos(pdf)[0])
        elif isinstance(v, str):
            raise ValueError(f"report '{label}': '{v}' inválido (só número, PROW ou PCOL)")
        else:
            out.append(v)
    return out


def _anchor(pdf, cfg, label=''):
    """Âncora [col, lin] de location/pos (grade, origem área útil)."""
    loc = cfg.get('location', cfg.get('pos', [0, 0])) or [0, 0]
    if list(loc)[:2] == [0, 0]:
        return
    from ajsystem.defs.report import _CursorExpr as _CE
    for _v in list(loc)[:2]:
        if isinstance(_v, bool) or (not isinstance(_v, (int, float))
                                    and not isinstance(_v, _CE)
                                    and _v not in ('PROW', 'PCOL')):
            raise ValueError(f"report '{label}': âncora [col, lin] inválida: {list(loc)!r}")
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)  # referência fixa da grade
    col_w = pdf.get_string_width('0') or 2.0
    c, r = _resolve_tokens(pdf, list(loc)[:2], label)
    pdf.set_xy(pdf.l_margin + c * col_w, pdf.t_margin + r * ROW_CELL)


def _eval_tab_value(pdf, v, label):
    """Número, constante PCOL/PROW (±N) ou string 'PCOL+20' (só ±, sem eval)."""
    import re as _re
    from ajsystem.defs.report import _CursorExpr as _CE
    if isinstance(v, bool):
        raise ValueError(f"report '{label}': TABS exige números ou PCOL/PROW±N")
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, _CE):
        if v.base not in ('PCOL', 'PROW'):
            raise ValueError(f"report '{label}': cursor '{v.base}' desconhecido")
        base = _grid_pos(pdf)[0 if v.base == 'PCOL' else 1]
        return base + v.offset
    if isinstance(v, str):
        m = _re.fullmatch(r'\s*(PCOL|PROW)\s*([+-]\s*\d+(?:\.\d+)?)?\s*', v)
        if m:
            base = _grid_pos(pdf)[0 if m.group(1) == 'PCOL' else 1]
            return base + float(m.group(2).replace(' ', '')) if m.group(2) else base
    raise ValueError(f"report '{label}': TABS exige números ou PCOL/PROW±N, veio {v!r}")


def _tab_x(pdf, tab, label):
    """X da parada tab:N (1-based). Y segue o fluxo."""
    tabs = getattr(pdf, '_tabs', None) or []
    if not isinstance(tab, int) or isinstance(tab, bool) or not 1 <= tab <= len(tabs):
        raise ValueError(f"report '{label}': tab:{tab} inválido (TABS tem {len(tabs)} paradas)")
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)
    col_w = pdf.get_string_width('0') or 2.0
    pdf.set_x(pdf.l_margin + tabs[tab - 1] * col_w)


def _place_item(pdf, kind, name, cfg, label):
    """Posicionamento pré-render: tab, location/pos ou volta à margem."""
    if 'tab' in cfg:
        if any(k in cfg for k in ('location', 'pos')):
            raise ValueError(f"report '{label}': tab não combina com location/pos")
        _tab_x(pdf, cfg['tab'], label)
        return
    if not any(k in cfg for k in ('location', 'pos')):
        pdf.set_x(pdf.l_margin)  # bloco: volta à margem, Y flui


def _cut_to_fit(pdf, txt, avail):
    """Trunca o excedente p/ caber em avail mm (corte seco)."""
    txt = txt or ''
    while txt and pdf.get_string_width(txt) + 2 > avail:
        txt = txt[:-1]
    return txt


def _render_flow_item(pdf, kind, name, cfg, instance, label, col_w):
    """FIELD/TEXT em fluxo datilográfico: segue na linha (PCOL avança);
    envolve p/ margem se não couber; trunca o excedente se maior que a linha.
    Posicionado (tab/location/pos) = absoluto, sem envoltório.
    """
    from ajsystem.core.text import render as _trender
    right = pdf.w - pdf.r_margin
    _fixed = any(k in cfg for k in ('tab', 'location', 'pos'))
    if kind == 'FIELD':
        if instance is None:
            raise ValueError(f"report '{label}': field '{name}' exige instância (documento)")
        from ajsystem.core.text import dotted_get as _dg
        fn, fmt = cfg.get('function'), cfg.get('format')
        if callable(fn):
            try:
                val = fn(instance)
            except Exception:
                val = None
        else:
            val = _dg(instance, cfg.get('field', name) or name)
        txt = _format_cell_value(val, fmt if fmt is not None else cfg.get('mask'))
        lbl = cfg.get('label') or name
        pdf.set_font(FONT_FAMILY, "B", FONT_ITEMS)
        lw = pdf.get_string_width(lbl + ': ') + 2
        pdf.set_font(FONT_FAMILY, "", FONT_ITEMS)
        vw = pdf.get_string_width(txt or '') + 2
        if not _fixed and pdf.get_x() + lw + vw > right + 0.01 and pdf.get_x() > pdf.l_margin + 0.01:
            pdf.ln(ROW_CELL)  # pcol+1>ncol -> pcol=1, prow+=1
        if lw + vw > right - pdf.l_margin:
            txt, vw = _cut_to_fit(pdf, txt, right - pdf.l_margin - lw), right - pdf.l_margin - lw
        pdf.set_font(FONT_FAMILY, "B", FONT_ITEMS)
        pdf.cell(lw, ROW_CELL, lbl + ': ', new_x="END")
        pdf.set_font(FONT_FAMILY, "", FONT_ITEMS)
        pdf.cell(vw, ROW_CELL, txt, new_x="END", new_y="TOP")
    else:  # TEXT
        from ajsystem.core.text import dotted_get as _dg
        txt = _trender(cfg.get('text', ''), lambda k: _dg(instance, k) if instance is not None else None, cfg.get('_fmt_opts'))
        pdf.set_font(FONT_FAMILY, cfg.get('font_style', ''), cfg.get('font_size', FONT_ITEMS))
        _w = cfg.get('width')
        if _w is not None:
            if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
                raise ValueError(f"report '{label}': width deve ser cols > 0")
            pdf.set_font(FONT_FAMILY, "", FONT_CELL)
            _w = _w * (pdf.get_string_width('0') or 2.0)
            pdf.set_font(FONT_FAMILY, cfg.get('font_style', ''), cfg.get('font_size', FONT_ITEMS))
        else:
            _w = pdf.get_string_width(txt or '') + 2
        if not _fixed and pdf.get_x() + _w > right + 0.01 and pdf.get_x() > pdf.l_margin + 0.01:
            pdf.ln(ROW_CELL)
        if _w > right - pdf.l_margin:
            txt, _w = _cut_to_fit(pdf, txt, right - pdf.l_margin), right - pdf.l_margin
        pdf.cell(_w, ROW_CELL, txt, align=cfg.get('align', 'L'), new_x="END", new_y="TOP")


def _render_items(pdf, items, instance, report, reset_tabs=True):
    """Itens inline em ordem, antes da tabela. rows_before/after em linhas.

    TABS ([n...], diretiva) ancora X por tab:N (Y no fluxo); POS ([c,r])
    salta o cursor; PROW/PCOL valem em âncora. reset_tabs=False preserva as
    paradas vigentes (uso interno do header, que renderiza item a item).
    """
    from ajsystem.core.geom import normalize as _gloc, to_mm as _gmm
    from ajsystem.core.text import render as _trender
    label = report.label if report is not None else ''
    if reset_tabs:
        pdf._tabs = None
    pdf.set_font(FONT_FAMILY, "", FONT_CELL)  # referência fixa da grade
    col_w = pdf.get_string_width('0') or 2.0
    for it in items or []:
        kind, name, cfg = _split_item(it, label)
        if kind == 'FIELDS':
            raise ValueError(f"report '{label}': FIELDS deve ser expandido no apply (do_report)")
        if kind in ('FIELD', 'TEXT') and cfg.get('when') is not None:
            from ajsystem.core.text import eval_when as _ew
            if not _ew(instance, cfg['when']):
                continue
        if kind == 'TABS':
            _stops = [_eval_tab_value(pdf, _s, label) for _s in (cfg.get('values') or [])]
            if sorted(_stops) != list(_stops):
                raise ValueError(f"report '{label}': TABS deve vir em ordem crescente")
            pdf._tabs = list(_stops)
            continue
        if kind == 'CALL':
            try:
                _txt = cfg['fn'](instance) if instance is not None else ''
            except Exception:
                _txt = ''
            if _txt:
                pdf.set_font(FONT_FAMILY, "", FONT_ITEMS)
                pdf.cell(0, ROW_CELL, _txt, new_x="LMARGIN", new_y="NEXT")
            continue
        if kind == 'POS':
            _c, _r = _resolve_tokens(pdf, cfg.get('values'), label)
            for _v in (_c, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)):
                    raise ValueError(f"report '{label}': POS exige [col, lin]")
            pdf.set_xy(pdf.l_margin + _c * col_w, pdf.t_margin + _r * ROW_CELL)
            continue
        rb, ra = int(cfg.get('rows_before', 0) or 0), int(cfg.get('rows_after', 0) or 0)
        if rb:
            pdf.ln(rb * ROW_CELL)
        _place_item(pdf, kind, name, cfg, label)
        if kind in ('FIELD', 'TEXT'):
            _render_flow_item(pdf, kind, name, cfg, instance, label, col_w)
        elif kind == 'IMAGE':
            src = cfg.get('path') or (getattr(instance, cfg.get('field', name), None) if instance is not None else None)
            if not src:
                raise ValueError(f"report '{label}': IMAGE sem path/field")
            from flask import current_app
            import os as _os
            path = src if _os.path.isabs(str(src)) else _os.path.join(current_app.root_path, str(src))
            x, y, w, hh = _image_box(pdf, cfg.get('location'), path)
            pdf.image(path, x=x, y=y, w=w, h=hh)
        else:  # LINE / BOX / CIRCLE
            g = _gmm(_gloc(kind, cfg.get('location')), ROW_CELL, col_w)
            ox, oy = pdf.l_margin, pdf.t_margin
            if kind == 'LINE':
                pdf.line(ox + g['x1'], oy + g['y1'], ox + g['x2'], oy + g['y2'])
            elif kind == 'BOX':
                pdf.rect(ox + g['x'], oy + g['y'], g['w'], g['h'])
            else:
                pdf.ellipse(ox + g['x'] - g['rx'], oy + g['y'] - g['ry'],
                            2 * g['rx'], 2 * g['ry'])
        if ra:
            pdf.ln(ra * ROW_CELL)


def gerar_pdf_relatorio(report: Report, data: list = None, logo_path: str = None,
                        instance=None, title_substitutions: dict = None) -> DocPDFReport:
    """Gera PDF genérico a partir de um Report."""
    data = data or []

    pdf = DocPDFReport(report)
    pdf.set_auto_page_break(auto=report.auto_page_break, margin=report.margin_bottom)
    pdf.set_margins(report.margin_left, report.margin_top, report.margin_right)

    # Aplicar logo customizado
    h_cfg = report.header if isinstance(report.header, dict) else {}
    if logo_path and (h_cfg or {}).get('show_logo', True):
        pdf._header.logo_path = logo_path

    # Substituições extras no título
    if title_substitutions:
        pdf._title_substitutions = title_substitutions

    # Definir instância
    pdf.set_instance(instance)

    # Primeira página
    pdf.add_page()

    # Before table (do corpo)
    _body = _report_body(report)
    _before = getattr(_body, 'before', None) if _body else None
    if callable(_before) and instance:
        _before = _before(instance) or []
    if _before:
        _render_table_lines(pdf, _before, instance)

    # Itens inline em ordem (body.items), antes da tabela
    _items = getattr(_body, 'items', None) if _body else None
    if _items:
        _render_items(pdf, _items, instance, report)
        _bl = _body.get('table') if isinstance(_body, dict) else getattr(_body, 'table', None)
        if isinstance(_bl, dict) and _bl.get('rows_before'):
            pdf.ln(int(_bl['rows_before']) * ROW_CELL)

    # Tabela
    tbl = _build_table(report)
    if tbl.columns:
        _render_table(pdf, tbl.columns, data, tbl.totals,
                      instance, report=report)
    if tbl.rows_after:
        pdf.ln(tbl.rows_after * ROW_CELL)

    # After table (do corpo)
    _after = getattr(_body, 'after', None) if _body else None
    if callable(_after) and instance:
        _after = _after(instance) or []
    if _after:
        _render_table_lines(pdf, _after, instance)
    if tbl.after and instance:
        if isinstance(tbl.after, list):
            _render_items(pdf, tbl.after, instance, report)
        else:
            txt = tbl.after
            if callable(txt):
                try:
                    txt = txt(instance)
                except Exception:
                    txt = ''
            if txt:
                pdf.ln(GAP_AFTER_TABLE)
                pdf.set_font(FONT_FAMILY, "", FONT_ITEMS)
                pdf.cell(0, ROW_CELL, txt, new_x="LMARGIN", new_y="NEXT")

    # Texts avulsos
    if report.texts:
        for txt in report.texts:
            if txt.when == 'end_of_report':
                pdf.ln(GAP_TEXTS)
                pdf.set_font(FONT_FAMILY, txt.font_style, txt.font_size)
                pdf.cell(0, txt.font_size * 0.5, txt.text, align=txt.align,
                         new_x="LMARGIN", new_y="NEXT")

    return pdf
