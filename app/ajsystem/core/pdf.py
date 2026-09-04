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

from app.ajsystem.core.utils import apply_transform, fmt_money, normalize_currency
from app.ajsystem.defs.report import (
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


@dataclass
class _ReportTable:
    """Tabela do relatório (interno de renderização)."""
    columns: ReportColumns = None
    footer: bool = False
    footer_label: str = 'Total'
    after: Optional[object] = None
    rows_before: int = 1
    rows_after: int = 1


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
    h = {**_HEADER_DEFAULTS, **(report.header or {})}

    # Logo: nested (deep merge) ou flat
    logo_cfg = {**_HEADER_DEFAULTS.get('logo', {}), **(h.get('logo') or {})}
    pos = logo_cfg.get('position', h.get('logo_align', 'N'))
    show_logo = pos != 'N'
    logo_lines = logo_cfg.get('lines', 4)
    logo_align = 'C' if pos == 'N' else pos

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
        line=bool(h.get('line', False)),
    )


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
    return _ReportTable(
        columns=columns,
        footer=t.get('footer', False),
        footer_label=t.get('footer_label', 'Total'),
        after=t.get('after'),
        rows_before=t.get('rows_before', 1),
        rows_after=t.get('rows_after', 1),
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


def _deep_attr(obj, path):
    if obj is None:
        return None
    for part in path.split('.'):
        if obj is None:
            return None
        try:
            obj = getattr(obj, part)
        except AttributeError:
            try:
                obj = obj[part]
            except (TypeError, KeyError, IndexError):
                return None
    return obj


class DocPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}/{{nb}}", align="C")


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

        # Resolver logo_width
        logo_w = h.logo_width
        if logo_w is None:
            logo_w = self.w * 0.25 if h.layout == 'logo_left' else 60

        if h.layout == 'logo_left':
            self._render_header_logo_left(h, logo_w)
        else:
            # Logo centralizado
            if h.show_logo:
                logo = h.logo_path
                if logo:
                    if h.logo_align == 'C':
                        x = self.w / 2 - logo_w / 2
                    elif h.logo_align == 'R':
                        x = self.w - self.r_margin - logo_w
                    else:
                        x = self.l_margin
                    self.image(logo, x=x, w=logo_w, h=0)
                    self.ln(h.logo_height)
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
            self.set_font("Helvetica", h.title_font_style, h.title_font_size)
            self.cell(right_w, h.title_font_size * 0.6, title, align='C',
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(2)

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
            self.set_font("Helvetica", h.title_font_style, h.title_font_size)
            self.cell(0, h.title_font_size * 0.6, title, align=h.title_align,
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(4)

        # Subtitle
        if h.subtitle:
            self.set_font("Helvetica", "", h.subtitle_font_size)
            self.cell(0, h.subtitle_font_size * 0.5, h.subtitle,
                      align=h.subtitle_align, new_x="LMARGIN", new_y="NEXT")
            self.ln(3)

        # Header fields
        if h.fields and self._instance:
            self._render_header_fields(h.fields, h.field_columns)

        if not h.on_each_page:
            self.ln(4)

    def _render_header_fields(self, fields, num_columns, x_start=None, area_width=None):
        parsed = [parse_header_field(f) for f in fields]
        if x_start is None:
            x_start = self.l_margin
        if area_width is None:
            area_width = self.w - self.l_margin - self.r_margin
        col_w = area_width / num_columns
        y0 = self.get_y()
        row_h = 6
        col = 0
        row = 0
        for rf in parsed:
            x = x_start + col * col_w
            y = y0 + row * row_h
            # Label (bold)
            self.set_xy(x, y)
            self.set_font("Helvetica", "B", 9)
            lbl = (rf.label or rf.field or '') + ':'
            self.cell(col_w * 0.4, row_h, lbl, new_x="END")
            # Value
            self.set_font("Helvetica", "", 9)
            val = self._get_field_value(rf)
            align = 'R' if rf.align == 'right' else 'L'
            self.cell(col_w * 0.6, row_h, val, align=align, new_x="END")
            col += 1
            if col >= num_columns:
                col = 0
                row += 1
        self.set_y(y0 + (row + (1 if col > 0 else 0)) * row_h + 4)

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
            self.set_y(-15)
            self.set_font("Helvetica", "I", f.font_size)
            self.cell(0, 10, f.separator.join(parts), align=f.align)


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


def _format_cell_value(val, fmt: str) -> str:
    """Formata valor para exibição na célula."""
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
    pdf.set_font("Helvetica", "B", 9)
    row_h = 7
    for i, col in enumerate(cols):
        align = 'C' if col.align == 'center' else ('R' if col.align == 'right' else 'L')
        nx = "LMARGIN" if i == len(cols) - 1 else "END"
        ny = "NEXT" if i == len(cols) - 1 else "TOP"
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], row_h, col.label or col.field, border=0, align=align, new_x=nx, new_y=ny)
    _draw_hline(pdf, x_start, total_w)


def _render_data_row(pdf, cols, col_widths, row, x_start, agg_values):
    """Renderiza uma linha de dados."""
    pdf.set_font("Helvetica", "", 9)
    row_h = 6
    for i, col in enumerate(cols):
        val = _get_cell_value(row, col)
        txt = _format_cell_value(val, col.format)
        align = 'R' if col.align == 'right' else ('C' if col.align == 'center' else 'L')
        nx = "LMARGIN" if i == len(cols) - 1 else "END"
        ny = "NEXT" if i == len(cols) - 1 else "TOP"
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], row_h, txt, border=0, align=align, new_x=nx, new_y=ny)
        if col.agg == 'sum' and val is not None:
            try:
                agg_values[col.field] += float(val)
            except (ValueError, TypeError):
                pass
    if pdf._report.show_table_lines:
        _draw_hline(pdf, x_start, sum(col_widths))


def _render_footer_row(pdf, cols, col_widths, footer_label, agg_values, x_start, total_w):
    """Renderiza linha de total."""
    pdf.set_font("Helvetica", "B", 9)
    label_w = sum(col_widths[:-1])
    pdf.set_x(x_start)
    pdf.cell(label_w, 7, footer_label, border=0, align="R")
    last_val = ''
    for col in cols:
        if col.agg == 'sum':
            last_val = _format_cell_value(agg_values.get(col.field, 0), col.format)
    pdf.set_x(x_start + label_w)
    pdf.cell(col_widths[-1], 7, last_val, border=0, align="R", new_x="LMARGIN", new_y="NEXT")
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
    """Título do grupo — template `text`.

    '{campo}' = valor da linha com formatação da Entity (LIST → label);
    `{<g.field>}` = código do grupo (left aplicado); demais caracteres
    são literais. Ex.: '{indice}. {tipo}' → '1. Receitas'.

    Sem `text` → str(valor) do grupo.
    `transform`: 'upper' | 'title' | 'lower' aplicado ao texto final.
    """
    tpl = g.get('text')
    if not tpl:
        return apply_transform(str(val or ''), g.get('transform'))

    fmt_opts = g.get('_fmt_opts') or {}

    class _NS(dict):
        def __missing__(self, k):
            v = getattr(row, k, None) if row is not None else None
            o = fmt_opts.get(k)
            if o is not None and v is not None:
                v = o.get(v, v)
            return '' if v is None else str(v)

    ns = _NS()
    gv = val
    o = fmt_opts.get(g.get('field'))
    if o is not None and gv is not None:
        gv = o.get(gv, gv)
    ns[g['field']] = gv
    return apply_transform(tpl.format_map(ns), g.get('transform'))


def _render_group_header(pdf, g, val, xs, tw, pos, row=None):
    txt = apply_transform(_group_title(g, val, row=row), g.get('transform'))
    style = 'B' if g.get('bold', True) else ''
    size = 11 if pos == 2 else 10
    indent = 2 if pos == 2 else 6
    height = 8 if pos == 2 else 7
    pdf.set_font("Helvetica", style, size)
    pdf.set_x(xs + indent)
    pdf.cell(tw - indent, height, txt, border=0,
             new_x="LMARGIN", new_y="NEXT")


def _render_group_line(pdf, g, val, xs, tw, row=None):
    """Linha `pos=1` — interna à tabela, texto corrido na largura da tabela."""
    txt = apply_transform(_group_title(g, val, row=row), g.get('transform'))
    style = 'B' if g.get('bold', True) else ''
    pdf.set_font("Helvetica", style, 9)
    indent = max(1, int(g.get('left', 1) or 1)) * 4
    height = 7
    pdf.set_x(xs + indent)
    pdf.cell(tw - indent, height, txt, border=0,
             new_x="LMARGIN", new_y="NEXT")


def _render_group_total(pdf, g, cols, cw, xs, acc):
    if not any(c.agg for c in cols):
        return
    pdf.set_font("Helvetica", "B", 9)
    label_w = sum(cw[:-1])
    pdf.set_x(xs)
    pdf.cell(label_w, 7, "Total", border=0, align="R")
    last_i = max(i for i, c in enumerate(cols) if c.agg == 'sum') \
        if any(c.agg == 'sum' for c in cols) else None
    for i, col in enumerate(cols):
        if col.agg == 'sum':
            v = _format_cell_value(acc.get(col.field, 0), col.format)
            is_last = i == len(cols) - 1
            pdf.set_x(xs + sum(cw[:i]))
            pdf.cell(cw[i], 7, v, border=0, align="R",
                     **({'new_x': "LMARGIN", 'new_y': "NEXT"} if is_last else {}))


def _walk_field_groups(pdf, cols, cw, tw, xs, data, gs,
                       agg_values, header_h, report):
    """Grupos por mudança de valor do campo (specs normalizadas)."""
    lines_after = (_body_table(report)).get('rows_after', 1) if report else 1
    show_lines = bool(report.show_table_lines) if report else False
    prev = [None] * len(gs)
    accs = [{c.field: 0 for c in cols if c.agg} for _ in gs]
    started = False
    table_open = False   # nada foi desenhado ainda — evita fechar tabela fantasma
    gera_cab = True

    def close_level(i):
        g = gs[i]
        if not started:
            return
        if g.get('total', True):
            _render_group_total(pdf, g, cols, cw, xs, accs[i])
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
                        pdf.ln(lines_after * 6)
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
            started = True

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
                    v = getattr(row, c.field, 0) or 0
                    acc[c.field] += v

    # fecha grupos remanescentes
    for i in range(len(gs) - 1, -1, -1):
        close_level(i)
    if show_lines:
        _draw_hline(pdf, xs, tw)


def _render_table(pdf: DocPDFReport, columns: ReportColumns,
                  data: list, show_footer: bool = False,
                  footer_label: str = 'Total', instance=None,
                  draw_top_line=True, report=None):
    """Renderiza uma tabela no PDF com centralização, sem laterais,
    page break com repetição de cabeçalho e shrink-to-fit."""
    cols = list(columns)
    if not cols:
        return


    col_widths, total_w, x_start = _calc_col_widths(pdf, cols)

    # Verificar largura mínima
    for i, col in enumerate(cols):
        if col_widths[i] < MIN_COL_WIDTH:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 10, f"Erro: coluna '{col.label or col.field}' muito estreita "
                     f"({col_widths[i]:.1f}mm < {MIN_COL_WIDTH}mm). "
                     f"Largura insuficiente para o relatório.",
                     align="C", new_x="LMARGIN", new_y="NEXT")
            return

    # Dados — grupos por mudança de valor (specs normalizadas em _apply_entity)
    agg_values = {c.field: 0 for c in cols if c.agg}
    header_h = 7 + 6
    gera_cab = True
    gs = [g for g in _body_table(report).get('hierarchy', [])
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
    if not show_footer:
        _table_close(pdf, x_start, total_w)

    # Table footer (total) — com sua própria linha de fechamento
    if show_footer:
        footer_h = 7
        if _check_page_break(pdf, footer_h):
            _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
        _render_footer_row(pdf, cols, col_widths, footer_label, agg_values, x_start, total_w)


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
            pdf.ln(8)
            continue
        pdf.ln(2)
        pdf.set_font("Helvetica", style, size)
        pdf.cell(w, size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")


def gerar_pdf_relatorio(report: Report, data: list = None, logo_path: str = None,
                        instance=None, title_substitutions: dict = None) -> DocPDFReport:
    """Gera PDF genérico a partir de um Report."""
    data = data or []

    pdf = DocPDFReport(report)
    pdf.set_auto_page_break(auto=report.auto_page_break, margin=report.margin_bottom)
    pdf.set_margins(report.margin_left, report.margin_top, report.margin_right)

    # Aplicar logo customizado
    h_cfg = report.header or {}
    if logo_path and h_cfg.get('show_logo', True):
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

    # Tabela
    tbl = _build_table(report)
    if tbl.columns:
        _render_table(pdf, tbl.columns, data, tbl.footer, tbl.footer_label,
                      instance, report=report)
    if tbl.rows_after:
        pdf.ln(tbl.rows_after * 6)

    # After table (do corpo)
    _after = getattr(_body, 'after', None) if _body else None
    if callable(_after) and instance:
        _after = _after(instance) or []
    if _after:
        _render_table_lines(pdf, _after, instance)
    if tbl.after and instance:
        txt = tbl.after
        if callable(txt):
            try:
                txt = txt(instance)
            except Exception:
                txt = ''
        if txt:
            pdf.ln(4)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, txt, new_x="LMARGIN", new_y="NEXT")

    # Texts avulsos
    if report.texts:
        for txt in report.texts:
            if txt.when == 'end_of_report':
                pdf.ln(4)
                pdf.set_font("Helvetica", txt.font_style, txt.font_size)
                pdf.cell(0, txt.font_size * 0.5, txt.text, align=txt.align,
                         new_x="LMARGIN", new_y="NEXT")

    return pdf
