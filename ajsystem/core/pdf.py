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
    """Normaliza totals -> {label, align, span, bline} | None."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: totals deve ser dict")
    for k in raw:
        if k not in ('label', 'align', 'span', 'bline'):
            raise ValueError(f"{where}: chave '{k}' inválida em totals")
    align = raw.get('align', 'C')
    if align not in ('L', 'C', 'R'):
        raise ValueError(f"{where}: align deve ser L|C|R")
    span = raw.get('span', 1)
    if isinstance(span, bool) or not isinstance(span, int) or span < 1:
        raise ValueError(f"{where}: span deve ser int >= 1")
    bline = raw.get('bline', False)
    if not isinstance(bline, bool):
        raise ValueError(f"{where}: bline deve ser bool")
    return {'label': raw.get('label', TOTALS_DEFAULT_LABEL),
            'align': align, 'span': span, 'bline': bline}


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
            logo_path=None,
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


def _draw_titulo(pdf, cfg, h, label='', instance=None, drawn=0,
                 title_size=None, title_style=None, sub_size=None, sub_style=''):
    """Desenha 1 TITLE. Devolve quantos títulos já foram desenhados (o próprio
    contador, quando o `when` pula).

    Um só, para o header e para o corpo: os dois têm a mesma cascata (1º
    título = grande/negrito, demais = subtítulo) e a mesma conta de `size * 0.6`
    de altura. Os **defaults chegam por argumento** porque só o header tem
    `h.title_font_size`/`h.title_font_style`; no corpo são as constantes.

    `font_size`/`font_style` declarados mudam a fonte sem mudar a POSIÇÃO — o
    1º continua sendo o 1º (respiro de título, estilo padrão), que é o que
    separa "declarar o tamanho" de "virar subtítulo".
    """
    if cfg.get('when') is not None:
        from ajsystem.core.text import eval_when as _ew
        if not _ew(instance, cfg['when']):
            return drawn          # pulado: não gasta a posição da cascata
    first = drawn == 0
    txt = cfg.get('text', cfg.get('label', label))
    if 'tab' in cfg:
        if any(k in cfg for k in ('location', 'pos')):
            raise ValueError(f"report '{label}': tab não combina com location/pos")
        _tab_x(pdf, cfg['tab'], label)
    elif any(k in cfg for k in ('location', 'pos')):
        _anchor(pdf, cfg, label)
    else:
        pdf.set_x(pdf.l_margin)  # bloco: volta à margem, Y flui
    if callable(txt) and instance:
        txt = txt(instance)
    elif instance and isinstance(txt, str) and '{' in txt:
        # Template de verdade: `{status}` sai como RÓTULO (o catálogo do field
        # vem em `_fmt_opts`, anexado no apply) e não como o código. Antes só
        # `{id}` era trocado, e qualquer outro campo saía cru no título.
        from ajsystem.core.text import render as _trender, dotted_get as _tdg
        txt = _trender(txt, lambda k: _tdg(instance, k) if instance is not None else None,
                       cfg.get('_fmt_opts') or {})
    if hasattr(pdf, '_title_substitutions'):
        for k, v in pdf._title_substitutions.items():
            txt = (txt or '').replace('{' + k + '}', str(v))
    size = cfg.get('font_size', title_size if first else sub_size)
    style = cfg.get('font_style', title_style if first else sub_style)
    if isinstance(size, bool) or not isinstance(size, (int, float)) or size <= 0:
        raise ValueError(f"report '{label}': font_size do TITLE deve ser > 0, veio {size!r}")
    if style not in ('', 'B', 'I', 'BI'):
        raise ValueError(f"report '{label}': font_style do TITLE: ''|B|I|BI, veio {style!r}")
    if cfg.get('options') is not None and not isinstance(cfg['options'], dict):
        raise ValueError(
            f"report '{label}': 'options' do TITLE deve ser dict "
            f"(catálogo {{codigo: rótulo}}), veio {type(cfg['options']).__name__}")
    # TITLE sempre centralizado por default; outro align só se declarado.
    align = cfg.get('align', 'C')
    pdf.set_font(FONT_FAMILY, style, size)
    _w = cfg.get('width')
    if _w is not None:
        if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
            raise ValueError(f"report '{label}': width deve ser cols > 0")
        _w = _w * _col_unit(pdf)
        pdf.set_font(FONT_FAMILY, style, size)
    else:
        _w = 0  # coluna corrente até o fim da linha
    pdf.cell(_w, size * 0.6, txt or '', align=align, new_x="LMARGIN", new_y="NEXT")
    _mark_content(pdf)
    pdf.ln(GAP_TITLE if first else GAP_SUBTITLE)
    return drawn + 1


def _render_header_items(self, h):
    """Header em forma lista: LOGO/TITLE (cascata)/FIELD/TEXT/IMAGE/formas."""
    from ajsystem.defs.report import parse_report_item
    from ajsystem.core.text import render as _trender
    label = self._report.label if getattr(self, '_report', None) else ''
    items = [parse_report_item(it, label) for it in (h.raw_header or [])]
    self._tabs = None
    self._gridfont = None
    self._ind = None
    titles = 0
    for item in items:
        cfg = item.config
        if item.kind == 'FONT':
            if not cfg.get('font') and cfg.get('cpp') is None:
                self._gridfont = None  # FONT() nu = restaura o default
            else:
                self._gridfont = _resolve_font(cfg, label)
            continue
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
            _c, _r = _resolve_tokens(self, list(_vals), label)
            for _v in (_c, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)):
                    raise ValueError(f"report '{label}': POS exige [col, lin]")
            self.set_xy(self.l_margin + _c * _col_unit(self),
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
            _mark_content(self)
        elif item.kind == 'TITLE':
            titles = _draw_titulo(self, cfg, h, label, instance=self._instance,
                                  drawn=titles,
                                  title_size=h.title_font_size,
                                  title_style=h.title_font_style,
                                  sub_size=h.subtitle_font_size, sub_style='')
        elif item.kind == 'TITLES':
            # Vários TITLE numa tacada. Não delega ao `_render_items`: ali não
            # existem a cascata nem os defaults do header, e o `text` de
            # template também não. O `when` de cada entrada é decidido antes do
            # contador, então subtítulo pulado não vira título grande.
            for _sub in cfg.get('items') or []:
                _k, _n, _cfg = _split_item(_sub, label)
                if _k != 'TITLE':
                    raise ValueError(
                        f"report '{label}': TITLES aceita só TITLE, veio {_k!r}")
                titles = _draw_titulo(self, _cfg, h, label, instance=self._instance,
                                       drawn=titles,
                                       title_size=h.title_font_size,
                                       title_style=h.title_font_style,
                                       sub_size=h.subtitle_font_size, sub_style='')
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
        self._in_header = True
        try:
            self._header_inner(h)
        finally:
            self._in_header = False

    def _header_inner(self, h):
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
        from ajsystem.core.formats import normalize_currency as _nc
        if rf.format == 'brl':
            return _fmt(val)
        if rf.format is True or isinstance(rf.format, int):
            return fmt_money(val, rf.format)
        if rf.format == 'date' and hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y')
        if rf.format == 'datetime' and hasattr(val, 'strftime'):
            return val.strftime('%d/%m/%Y %H:%M')
        if (isinstance(rf.format, str) and not _is_mask(rf.format)
                and _nc(rf.format) is not None):
            return fmt_money(val, rf.format)
        if _is_mask(rf.format):
            from ajsystem.core.formats import format as _format
            try:
                return _format(val, rf.format)
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
    from ajsystem.core.formats import (
        normalize_currency as _nc, fmt_money as _fmoney,
        fmt_num as _fnum, _fmt_dec as _fdec,
    )
    if fmt == 'brl':
        return _fmt(val)
    if fmt is True or isinstance(fmt, int):
        return _fmoney(val, fmt)
    if fmt == 'date' and hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y')
    if fmt == 'datetime' and hasattr(val, 'strftime'):
        return val.strftime('%d/%m/%Y %H:%M')
    if isinstance(fmt, str) and not _is_mask(fmt) and _nc(fmt) is not None:
        return _fmoney(val, fmt)
    if _is_mask(fmt):
        from ajsystem.core.formats import format as _format
        try:
            return _format(val, fmt)
        except Exception:
            return str(val)
    if fmt == 'int':
        try:
            return str(int(val))
        except (ValueError, TypeError):
            return str(val)
    if fmt == 'float':
        try:
            return _fdec(val, 3, True)
        except (ValueError, TypeError):
            return str(val)
    return str(val)




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


PAPER_FIT_MSG = ('Largura do papel insuficiente para relatorio. '
                 'Mude orientação ou tipo de papel.')


def _calc_col_widths(pdf, cols, cpp=0):
    """Converte widths (ch) → mm no pitch nominal (tabela sempre draft).

    - Colunas com `width` (ch) → mm exato em 25.4/cpp;
    - Sem nenhuma width → divisão igual;
    - Com widths parciais → restante dividido entre as sem width;
    - Todas com width → bloco centrado no disponível.
    """
    from ajsystem.defs.fonts import CPP as _CPP
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    unit = 25.4 / _CPP[cpp]
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


MIN_COL_CHARS = 6  # piso de legibilidade por coluna (em caracteres)


def _fit_table(pdf, cols, label):
    """Auto-fit: cpp 0→3 (10/12/17/20); primeiro que cabe (total + piso em
    caracteres). Tabela é sempre draft; font/cpp/size dentro dela = fail-fast."""
    from ajsystem.defs.fonts import CPP as _CPP
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    for cpp in sorted(_CPP):
        col_widths, total_w, x_start = _calc_col_widths(pdf, cols, cpp)
        _floor = MIN_COL_CHARS * 25.4 / _CPP[cpp]
        if total_w <= avail_w + 0.01 and all(w + 0.01 >= _floor for w in col_widths):
            return col_widths, total_w, x_start, cpp
    raise ValueError(f"report '{label}': {PAPER_FIT_MSG}")


def _check_page_break(pdf, needed_h):
    """Verifica se há espaço. Se não, fecha tabela e adiciona página."""
    if pdf.get_y() + needed_h + pdf.b_margin <= pdf.h:
        return False
    pdf.add_page()
    return True


def _mark_content(pdf):
    """Conteúdo impresso: libera a próxima régua."""
    pdf._ruled = False


def _draw_hline(pdf, x_start, total_w):
    """Linha horizontal (sem laterais). Régua seguida sem conteúdo = ignorada."""
    if getattr(pdf, '_ruled', False):
        return
    y = pdf.get_y()
    pdf.line(x_start, y, x_start + total_w, y)
    pdf._ruled = True


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
    _mark_content(pdf)
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
    _mark_content(pdf)
    if pdf._report.show_table_lines:
        _draw_hline(pdf, x_start, sum(col_widths))


def _render_extend(pdf, cols, col_widths, x_start, total_w, items, instance, report):
    """Linhas dentro do quadro (table.extend): tuplas, spans, LINE/LF/CR."""
    import re as _re
    from ajsystem.core.text import render as _trender, eval_when as _ew, dotted_get as _dg
    label = report.label if report is not None else ''
    n = len(cols)
    _ALIGN = {'left': 'L', 'center': 'C', 'right': 'R'}

    def _span_xw(a, b):
        return x_start + sum(col_widths[:a - 1]), sum(col_widths[a - 1:b])

    _stayed = False
    for it in items or []:
        # `LINE()` aqui é a régua da própria tabela: `_draw_hline` (e não
        # `pdf.line`), para valer o latch que impede duas réguas seguidas sem
        # conteúdo entre elas. Fora do `extend` a régua é intenção do autor e
        # desenha sempre.
        if isinstance(it, dict) and 'LINE' in it:
            if _stayed:
                # a régua começa uma linha: fecha a anterior, que ficou pela
                # esquerda. Sem isso ela nasceria por cima do texto daquela.
                pdf.ln(ROW_CELL)
                _stayed = False
            if _check_page_break(pdf, ROW_CELL):
                _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
            _draw_hline(pdf, x_start, total_w)
            # NÃO avança: a régua no `extend` é DIVISOR, não linha. Ela nasce no
            # topo da faixa e a linha seguinte se apoia nela — a régua ocupa o
            # lugar da faixa em branco que o `ln(ROW_CELL)` custaria, que era o
            # jeito de o autor bancar um separador e ganhar uma linha vazia.
            continue
        if isinstance(it, str):
            if it not in ('LF', 'CR'):
                raise ValueError(
                    f"report '{label}': extend aceita tupla, LINE(), LF ou CR "
                    f"(a régua é LINE(), não a string 'LINE')")
            if it == 'LF':
                pdf.ln(ROW_CELL)
            else:
                pdf.set_x(x_start)
            _stayed = False
            continue
        if not (isinstance(it, tuple) and 2 <= len(it) <= 3):
            raise ValueError(f"report '{label}': extend exige (col, texto[, props])")
        _col, _text = it[0], it[1]
        _props = dict(it[2]) if len(it) == 3 else {}
        for _fk in ('font', 'cpp', 'font_size'):
            if _fk in _props:
                raise ValueError(f"report '{label}': '{_fk}' não vale em tabela (sempre cpp=0)")
        if _props.get('font_style') not in (None, '', 'B', 'I', 'BI'):
            raise ValueError(f"report '{label}': font_style em tabela: ''|B|I|BI")
        if not isinstance(_text, str):
            raise ValueError(f"report '{label}': texto do extend deve ser str")
        if isinstance(_col, list):
            if len(_col) != 2 or not all(isinstance(c, int) and not isinstance(c, bool) for c in _col):
                raise ValueError(f"report '{label}': span deve ser [a, b] ints")
            _a, _b = _col
            if not (1 <= _a <= _b <= n):
                raise ValueError(f"report '{label}': span [{_a}, {_b}] fora de 1..{n}")
            _x, _w, _align_dflt, _fmt_dflt = (*_span_xw(_a, _b), 'C', None)
        elif isinstance(_col, int) and not isinstance(_col, bool):
            if not 1 <= _col <= n:
                raise ValueError(f"report '{label}': col {_col} fora de 1..{n}")
            _x = x_start + sum(col_widths[:_col - 1])
            _w = col_widths[_col - 1]
            _cc = cols[_col - 1]
            _align_dflt, _fmt_dflt = _ALIGN.get(_cc.align, 'L'), _cc.format
        else:
            raise ValueError(f"report '{label}': col deve ser N ou [a, b]")
        _when = _props.get('when')
        if _when is not None and not _ew(instance, _when):
            continue
        if _check_page_break(pdf, ROW_CELL):
            _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
        _fo = _props.get('_fmt_opts') or {}
        _m = _re.fullmatch(r'{([\w.]+)}', (_text or '').strip())
        if _m and _props.get('format') is None and _fmt_dflt is not None:
            # Placeholder puro: herda formatação da coluna.
            _txt = _format_cell_value(_dg(instance, _m.group(1)) if instance is not None else None, _fmt_dflt)
        else:
            _txt = _trender(_text, lambda k: _dg(instance, k) if instance is not None else None, _fo)
        pdf.set_font(FONT_FAMILY, _props.get('font_style', ''), FONT_CELL)
        pdf.set_x(_x)
        _last_col = _b if isinstance(_col, list) else _col
        _stay = _last_col < n
        pdf.cell(_w, ROW_CELL, _txt, align=_props.get('align', _align_dflt),
                 new_x="END" if _stay else "LMARGIN",
                 new_y="TOP" if _stay else "NEXT")
        _stayed = _stay
        if _txt:
            _mark_content(pdf)
    if _stayed:
        pdf.ln(ROW_CELL)


def _render_footer_row(pdf, cols, col_widths, totals, agg_values, x_start, total_w, close=True):
    """Linha de total geral: rótulo nas SPAN primeiras + func por coluna agg."""
    _draw_hline(pdf, x_start, total_w)  # régua antes (interna, sempre)
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
    _mark_content(pdf)
    if close:
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
    _mark_content(pdf)


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
    _mark_content(pdf)


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
    if totals.get('bline'):
        _draw_hline(pdf, xs, sum(cw))
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
    _mark_content(pdf)


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
        if g.get('gline', g.get('line', True)):
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

    label = report.label if report is not None else ''
    col_widths, total_w, x_start, _cpp = _fit_table(pdf, cols, label)
    # Bordas reais p/ LTB/RTB em mm (última tabela vence; sem tabela = área
    # útil). Guarda em mm e converte na resolução: âncora/fluxo/IND vivem na
    # unidade da fonte corrente (`_col_unit`), que muda com FONT — gravar já
    # em cols do pitch da tabela brigava com o `ncol` da validação do IND.
    pdf._table_bounds = [x_start, x_start + total_w]
    pdf._table_cpp = _cpp

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

    # Extend (linhas dentro do quadro, após totais) + fechamento no fim.
    _ext = (_body_table(report).get('extend') or []) if report else []
    if totals is None and not _ext:
        _table_close(pdf, x_start, total_w)

    # Linha de total geral — com sua própria linha de fechamento
    if totals is not None:
        footer_h = ROW_FOOT
        if _check_page_break(pdf, footer_h):
            _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
        _render_footer_row(pdf, cols, col_widths, totals, agg_values, x_start, total_w,
                           close=True)
    if _ext:
        _render_extend(pdf, cols, col_widths, x_start, total_w, _ext,
                       instance, report)
        _table_close(pdf, x_start, total_w)


def _want_wrap(cfg, prop, label=''):
    """`wrap` declarado? Ausente = não quebra (o que `cell` sempre fez).

    A prop é binária de propósito: `rows` responderia "quantas linhas", e isso
    traz a pergunta de altura mínima ou caixa fixa junto. Quem só precisa do
    texto não vazar precisa de uma escolha só.
    """
    w = cfg.get('wrap')
    if w is None:
        return False
    if not isinstance(w, bool):
        raise ValueError(f"report '{label}': '{prop}' espera wrap booleano, veio {w!r}")
    return w


def _wrap_width(pdf, cols=None):
    """Largura de quebra: a prop `width` (em colunas) ou o resto da zona."""
    if cols:
        return cols * _col_unit(pdf)
    _x0, right = _flow_zone(pdf)
    return max(right - pdf.get_x(), 1.0)


# Espaço esticado pode no máximo DOBRAR (fração do espaço natural). Passando
# disso o olho lê "palavra        palavra" e não texto justificado — a 60 cols a
# sobra é 213% do espaço e o bloco serrilhado fica melhor que os buracos.
# `multi_cell` do fpdf2 DOCUMENTA `J: justify` mas NÃO implementa: escreve cada
# linha no x dela (medido, 102.5mm e 99.2mm numa coluna de 105.9mm), então
# justificar é nosso.
JUSTIFY_MAX = 1.0

# `MEMO` é parágrafo, e parágrafo se justifica: `J` é o DEFAULT e `L` é a
# exceção declarada. E como `J` aqui é um pedido com sanidade (`JUSTIFY_MAX`),
# o default não Produz buraco onde o autor não pediu — no máximo deixa a linha
# como `L`, que é a mesma coisa que pedir `L`.
MEMO_ALIGN = 'J'


def _wrap_linhas(pdf, txt, avail, first=None):
    """Quebra `txt` por palavra em linhas que caibam em `avail` mm.

    A casa só tinha `_cut_to_fit` (corte seco); parágrafo precisa de quebra de
    verdade. Palavra maior que a linha entra inteira e transborda — partir no
    meio de palavra em documento é pior que estourar a margem.

    `first` é a medida da PRIMEIRA linha, quando ela for menor que as demais —
    é o que faz o `recuo` do `MEMO`: a 1ª linha cabe em menos, as outras na
    medida do bloco. É literalmente `spaces(recuo) + texto`: o recuo entra no
    orçamento da linha, então ela sai mais curta, e as seguintes não se mexem.
    """
    palavras = (txt or '').split()
    if not palavras:
        return []
    linhas, atual = [], palavras[0]
    for k, p in enumerate(palavras[1:]):
        limite = (first if (not linhas and first is not None) else avail)
        if pdf.get_string_width(atual + ' ' + p) + 2 <= limite:
            atual += ' ' + p
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    return linhas


def _draw_bloco(pdf, linhas, x, w, h, font, size, style, align, recuo=0.0):
    """Desenha as linhas do bloco em `x`, largura `w`, linha de altura `h`.

    `J` distribui a sobra entre os espaços — só quando a estica fica dentro de
    `JUSTIFY_MAX`; acima disso cai em `L`, que é o que o olho prefere a um
    texto "justificado" com buracos. Quebra de página entre linhas como o resto
    do report (`_check_page_break`).

    `recuo` (mm) afasta SÓ a primeira linha, na medida da linha mais o seu
    recuo — a borda direita dela continua em `x + w`, porque `(x + recuo) +
    (w - recuo) = x + w`. O recuo entra como posição, e não como espaços no
    texto de propósito: se entrasse como texto, o `J` esticaria os espaços do
    recuo junto e o recuo cresceria só na 1ª linha.
    """
    espaco = pdf.get_string_width(' ')
    n_linhas = len(linhas)
    for i, ln in enumerate(linhas):
        _check_page_break(pdf, h)
        pdf.set_font(font, style, size)
        lx = x + recuo if (i == 0 and recuo) else x
        lw_m = w - recuo if (i == 0 and recuo) else w
        lw = pdf.get_string_width(ln) + 2
        extra = 0.0
        if align == 'J' and i < n_linhas - 1 and ' ' in ln:
            n_esp = ln.count(' ')
            sobra = lw_m - lw
            if sobra > 0:
                cand = sobra / n_esp
                if cand <= JUSTIFY_MAX * espaco:
                    extra = cand
        if align == 'C':
            x_linha = lx + (lw_m - lw) / 2
        elif align == 'R':
            x_linha = lx + (lw_m - lw)
        else:
            x_linha = lx
        if extra:
            # palavra a palavra: cada célula leva a largura da palavra mais o
            # espaço (esticado) que vem depois dela.
            palavras = ln.split(' ')
            ult = len(palavras) - 1
            pdf.set_x(x_linha)
            for k, palavra in enumerate(palavras):
                ww = pdf.get_string_width(palavra) + 2
                if k < ult:
                    ww += espaco + extra
                pdf.cell(ww, h, palavra, new_x='END', new_y='TOP')
            pdf.ln(h)
        else:
            pdf.set_x(max(x_linha, 0))
            pdf.cell(lw, h, ln, new_x='END', new_y='TOP')
            pdf.ln(h)
    if linhas:
        _mark_content(pdf)
    return pdf.get_y()


def _lines_de_callable(fn, instance, prop, label=''):
    """Chama a função de `before`/`after` e recusa item de volta.

    A função é chamada aqui, por instância, no meio da renderização — depois de
    `_apply_entity`, que é onde o item vira FIELD resolvido (label, catálogo,
    `calc`). Então item devolvido por callable não tem como ser resolvido: um
    LIST sairia com o código em vez do rótulo. Recusar aqui é melhor que deixar
    o item sair errado; a lista (não a função) é o caminho do item.
    """
    out = (fn(instance) or []) if instance is not None else []
    for line in out:
        if _is_item(line, label):
            raise ValueError(
                f"report '{label}': '{prop}' como função devolve LINHAS DE TEXTO; "
                f"item ({type(line).__name__}) não tem como ser resolvido contra a "
                f"Entity aí (a função roda depois do apply). Use a lista.")
    return out


def _render_table_lines(pdf, lines, instance=None, prop='body.after', report=None):
    """Renderiza `body.before` / `body.after`: LINHAS DE TEXTO **ou** items.

    `text`/`font_*`/`align`/`width`/`wrap` desenham uma linha de texto
    (avulsa, solta do resto do documento); qualquer item de `header`/`items`/
    `table.after` passa pelo mesmo `_render_items` das outras props — é o que
    permite declarar o preâmbulo do documento na mesma gramática do resto, em
    vez de montar em Python. O que NÃO entra é item vindo de callable: a função
    é chamada por instância no meio da renderização, então o item não passa por
    `_apply_entity` e sairia com o código cru em vez do rótulo (ver o fail-fast
    em `gerar_pdf_relatorio`).

    O texto passa pelo mesmo avaliador dos items (`core.text.render`), então
    `{campo}`, `{campo:brl}` e `{campo|fallback}` funcionam igual em `TEXT` e
    aqui. O catálogo é o do campo, derivado da Entity — para um texto que
    precisa de OUTRO catálogo (a frase de um documento), o item certo é
    `MEMO('campo', width, {'options': ...})`: mesmo override de field, e o
    catálogo entra pela Entity em vez de ser colado no texto.
    """
    from ajsystem.core.text import render as _trender
    for i, line in enumerate(lines or []):
        if _is_item(line):
            # `before`/`after` aceitam ITEM e linha de texto na mesma lista. Era
            # o contrário que valia: recusar item aqui foi a primeira metade da
            # correção (o item virava linha em branco, que é a pior falha), mas
            # a recusa empurrou o autor a montar o documento em Python. Agora a
            # lista é a mesma gramática de `header`/`items`/`table.after`, e a
            # linha de texto continua o que salva a indentação e o espaçador.
            _render_items(pdf, [line], instance, report, reset_tabs=False)
            continue
        text = line.get('text', '')
        if callable(text) and instance:
            text = text(instance)
        elif text:
            from ajsystem.core.text import dotted_get as _dg
            text = _trender(text,
                            lambda k: _dg(instance, k) if instance is not None else None,
                            line.get('_fmt_opts'))
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
        if _want_wrap(line, prop):
            # `cell` não quebra (fpdf2): o texto vaza para fora da página e a
            # ponta some. `multi_cell` quebra na largura da zona e cresce, que
            # é o que uma frase precisa.
            pdf.multi_cell(w or _wrap_width(pdf), size * 0.5, text, align=align,
                           new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(w, size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")
        if text:
            _mark_content(pdf)


# Props que fazem uma entrada ser LINHA DE TEXTO e não item. Fechado de
# propósito: `{'text': 'linha'}` e `{'campo': {...}}` são a mesma forma para o
# `_split_item` (dict de uma chave), e sem esta lista o texto mais comum do
# report viraria FIELD chamado `text`.
_TEXT_LINE_KEYS = frozenset(('text', 'font_size', 'font_style', 'align',
                             'width', 'wrap', '_fmt_opts'))


def _is_item(ent, label=''):
    """A entrada é um ITEM (`header`/`items`/`table.after`), e não uma linha de
    texto?

    Duas regras, na ordem: props de linha de texto ganham de item (o texto
    avulso é mais comum que o item no `before`), e o resto pergunta ao
    `_split_item` em vez de reimplementar o critério — foi o segundo bug da
    mesma família do `LIST/BOOL`: o classificador antigo só reconhecia chave
    MAIÚSCULA, e `FIELD('x', {...})` produz `{'x': {...}}` (minúscula), que
    caía no caminho de linha de texto e imprimia NADA. Quem decide passa a ser a
    mesma função que renderiza.
    """
    if isinstance(ent, str) or callable(ent):
        return True
    if isinstance(ent, dict):
        if _TEXT_LINE_KEYS & set(ent):
            return False
        try:
            _split_item(ent, label)
        except ValueError:
            return False
        return True
    return False





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
                if k in ('TABS', 'POS', 'IND'):
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': '{k}' exige lista")
                    return (k, k, {'values': list(v)})
                if k == 'TEXTS':
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': 'TEXTS' exige lista")
                    return (k, k, {'items': list(v)})
                if k == 'TITLES':
                    if not isinstance(v, list):
                        raise ValueError(f"report '{label}': 'TITLES' exige lista")
                    return (k, k, {'items': list(v)})
                if k in ('CR', 'LF', 'FF'):
                    return (k, k, v if isinstance(v, dict) else {})
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
    col_w = _col_unit(pdf)  # diretiva FONT ou referência fixa
    norm = _gloc('IMAGE', location)
    if norm[0] == 'IMAGE_ANCHOR':
        _, anchor, lines = norm
        iw, ih = _PIL.open(path).size
        area_cols = (pdf.w - pdf.l_margin - pdf.r_margin) / col_w
        norm = _gloc('IMAGE', _ra(anchor, lines, iw, ih, ROW_CELL, col_w, area_cols))
    g = _gmm(norm, ROW_CELL, col_w)
    return pdf.l_margin + g['x'], pdf.t_margin + g['y'], g['w'], g['h']


def _col_unit(pdf):
    """Largura da col em mm: nominal (25.4/cpp) sob FONT vigente ou ref fixa.

    Sem FONT = referência fixa (legado, byte-igual); com FONT, tudo
    (pos/tab/TABS/widths/ncol) usa o pitch nominal da fonte vigente.
    """
    spec = getattr(pdf, '_gridfont', None)
    if spec is None:
        pdf.set_font(FONT_FAMILY, "", FONT_CELL)  # referência fixa da grade
        return pdf.get_string_width('0') or 2.0
    return spec['col']


def _font_layers():
    """Camadas de fontes: framework < app.extends.fonts < Fonts da rota."""
    try:
        from flask import request, current_app
        from ajsystem.core.adapter import _override_ou
        from ajsystem.defs.fonts import module_fonts
        import importlib as _il
        from ajsystem.core.utils import module_blueprint
        app_layer = _override_ou('app.extends.fonts', 'Fonts', {}) or {}
        try:
            bp_name = request.blueprint
        except RuntimeError:
            return ({}, app_layer, {})
        if not bp_name:
            return ({}, app_layer, {})
        bp = current_app.blueprints.get(bp_name)
        mod = _il.import_module(bp.import_name) if bp is not None else None
        try:
            page_layer = module_fonts(mod) if mod is not None else {}
        except ImportError:
            page_layer = {}
        return ({}, app_layer, page_layer)
    except Exception:
        return ({}, {}, {})


def _resolve_font(cfg, label):
    """{'font': nome, 'cpp':?} -> {family, cpp, col} (fail-fast)."""
    from ajsystem.defs.fonts import resolve_font as _rf
    if not isinstance(cfg, dict) or not cfg.get('font'):
        raise ValueError(f"report '{label}': FONT exige {{font, ...}}")
    _fw, _app, _page = _font_layers()
    _extra = {k: v for k, v in cfg.items() if k not in ('font', 'cpp')}
    if _extra:
        raise ValueError(f"report '{label}': chaves {sorted(_extra)} inválidas em FONT")
    return _rf(cfg['font'], cfg.get('cpp'),
               types=[l for l in (_fw, _app, _page) if l])


def _font_default(pdf):
    """(family, size, style) p/ FIELD/TEXT sem tamanho próprio."""
    spec = getattr(pdf, '_gridfont', None)
    if spec is None:
        return (FONT_FAMILY, FONT_ITEMS, '')
    return (spec['family'], FONT_ITEMS, '')


def _apply_font(pdf, family, size, style):
    pdf.set_font(family, style, size)


def _grid_pos(pdf):
    """Cursor corrente em grade (PCOL, PROW)."""
    col_w = _col_unit(pdf)
    return ((pdf.get_x() - pdf.l_margin) / col_w,
            (pdf.get_y() - pdf.t_margin) / ROW_CELL, col_w)


def _usable_cols(pdf):
    """Total de cols da área útil na unidade vigente."""
    return (pdf.w - pdf.l_margin - pdf.r_margin) / _col_unit(pdf)


def _table_edges(pdf):
    """[l, r] da última tabela em cols da fonte corrente (ou área útil)."""
    tb = getattr(pdf, '_table_bounds', None)
    if tb is not None:
        col_w = _col_unit(pdf)
        return [(tb[0] - pdf.l_margin) / col_w, (tb[1] - pdf.l_margin) / col_w]
    return [0, _usable_cols(pdf)]


def _flow_zone(pdf):
    """(x0_mm, right_mm) do fluxo: região IND ou área útil."""
    ind = getattr(pdf, '_ind', None)
    if ind is not None:
        col_w = _col_unit(pdf)
        return pdf.l_margin + ind[0] * col_w, pdf.l_margin + ind[1] * col_w
    return pdf.l_margin, pdf.w - pdf.r_margin


def _resolve_tokens(pdf, values, label):
    """Troca cursores (literal ou constante) pelos valores. Só âncora
    (2 termos); em extensão (w/h/c2/r2/deltas) ou fora de lista = fail-fast."""
    from ajsystem.defs.report import _CursorExpr as _CE
    _gp = _grid_pos(pdf)
    _te = _table_edges(pdf)
    _ncol = _usable_cols(pdf)

    def _one(v):
        if isinstance(v, _CE):
            base, off = v.base, v.offset
        elif v in ('PCOL', 'PROW', 'LTB', 'RTB', 'NCOL'):
            base, off = v, 0
        else:
            return v
        if base == 'PCOL':
            return _gp[0] + off
        if base == 'PROW':
            return _gp[1] + off
        if base == 'LTB':
            return _te[0] + off
        if base == 'RTB':
            return _te[1] + off
        if base == 'NCOL':
            return _ncol + off
        raise ValueError(f"report '{label}': cursor '{base}' desconhecido")

    out = []
    for v in values:
        r = _one(v)
        if isinstance(r, str):
            raise ValueError(f"report '{label}': '{v}' inválido (só número ou cursor)")
        out.append(r)
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
    col_w = _col_unit(pdf)
    c, r = _resolve_tokens(pdf, list(loc)[:2], label)
    pdf.set_xy(pdf.l_margin + c * col_w, pdf.t_margin + r * ROW_CELL)


def _eval_tab_value(pdf, v, label):
    """Número, cursor (PCOL/PROW/LTB/RTB/NCOL ±N, const ou string) em TABS."""
    import re as _re
    from ajsystem.defs.report import _CursorExpr as _CE
    if isinstance(v, bool):
        raise ValueError(f"report '{label}': TABS exige números ou cursor±N")
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, _CE):
        return _resolve_tokens(pdf, [v], label)[0]
    if isinstance(v, str):
        m = _re.fullmatch(r'\s*(PCOL|PROW|LTB|RTB|NCOL)\s*([+-]\s*\d+(?:\.\d+)?)?\s*', v)
        if m:
            return _eval_cursor_str(pdf, m, label)
    raise ValueError(f"report '{label}': TABS exige números ou cursor±N, veio {v!r}")


def _eval_cursor_str(pdf, m, label):
    """Match de cursor±N em string -> valor."""
    from ajsystem.defs.report import _CursorExpr as _CE
    base, off = m.group(1), m.group(2)
    off = float(off.replace(' ', '')) if off else 0
    return _resolve_tokens(pdf, [_CE(base, off)], label)[0]


def _tab_x(pdf, tab, label):
    """X da parada tab:N (1-based). Y segue o fluxo."""
    tabs = getattr(pdf, '_tabs', None) or []
    if not isinstance(tab, int) or isinstance(tab, bool) or not 1 <= tab <= len(tabs):
        raise ValueError(f"report '{label}': tab:{tab} inválido (TABS tem {len(tabs)} paradas)")
    col_w = _col_unit(pdf)
    pdf.set_x(pdf.l_margin + tabs[tab - 1] * col_w)


def _elem_location(pdf, kind, cfg, label=''):
    """`location` de LINE/BOX/CIRCLE, resolvendo as formas sem coordenada.

    A factory guarda a INTENÇÃO (`mode`/`width`) porque a coordenada só existe
    no render — é o cursor e a zona daquele momento:

        'cursor' -> largura `width` a partir de (PCOL, PROW)
        'zona'   -> a indentação vigente (IND) ou, sem ela, a última tabela
        'pagina' -> a largura toda da área útil

    `geom` continua recebendo 4 números; só decide que ponto é ponto.
    """
    loc = cfg.get('location')
    if loc is not None:
        return loc
    mode = cfg.get('mode')
    if mode is None:
        raise ValueError(f"report '{label}': {kind} sem location nem mode")
    col_w = _col_unit(pdf)
    c, r, _cw = _grid_pos(pdf)
    if mode == 'cursor':
        w = cfg.get('width')
        if not isinstance(w, (int, float)) or isinstance(w, bool):
            raise ValueError(f"report '{label}': LINE(w) exige largura numérica, veio {w!r}")
        return [c, r, w, 0]
    if mode == 'pagina':
        return [0, r, _usable_cols(pdf), 0]
    if mode != 'zona':
        raise ValueError(f"report '{label}': LINE mode {mode!r} desconhecido")
    # A indentação manda; sem ela, a zona é a última tabela (fallback: área útil
    # — é o que `_table_edges` devolve quando ainda não houve tabela).
    ind = getattr(pdf, '_ind', None)
    if ind is not None:
        return [ind[0], r, ind[1] - ind[0], 0]
    esq, dir_ = _table_edges(pdf)
    return [esq, r, dir_ - esq, 0]


def _place_item(pdf, kind, name, cfg, label, line=True):
    """Posicionamento pré-render: âncora, fluxo, linha ou bloco.

    tab/location/pos = absoluto (inalterado). Sem âncora:
    - FIELD e TEXT com `width` = **fluxo**: herda o cursor (o item anterior
      deixou o X no fim dele); só entra na 1ª coluna da zona se o cursor
      está fora dela (início de bloco pós-tabela, zona nova do IND);
    - TEXT avulso sem âncora e sem `width` (line=True) = **linha própria**:
      começa na 1ª coluna da zona e, se o cursor não está lá (terminou um
      bloco de fluxo), avança a linha antes — é o "avanço de linha
      automático ao final" do bloco. Sub-item de TEXTS passa line=False e
      flui inline (o bloco é apertado; CR/LF controlam as quebras);
    - bloco (IMAGE/LINE/BOX/CIRCLE/CALL) = volta ao início, Y flui.
    """
    if 'tab' in cfg:
        if any(k in cfg for k in ('location', 'pos')):
            raise ValueError(f"report '{label}': tab não combina com location/pos")
        _tab_x(pdf, cfg['tab'], label)
        return
    if any(k in cfg for k in ('location', 'pos')):
        return
    x0, right = _flow_zone(pdf)
    if kind == 'TEXT' and line and cfg.get('width') is None:
        if pdf.get_x() > x0 + 0.01:
            pdf.ln(ROW_CELL)
        pdf.set_x(x0)
        return
    if kind in ('FIELD', 'TEXT'):
        if pdf.get_x() < x0 - 0.01 or pdf.get_x() > right + 0.01:
            pdf.set_x(x0)
        return
    pdf.set_x(x0)  # bloco: volta ao início, Y flui


def _cut_to_fit(pdf, txt, avail):
    """Trunca o excedente p/ caber em avail mm (corte seco)."""
    txt = txt or ''
    while txt and pdf.get_string_width(txt) + 2 > avail:
        txt = txt[:-1]
    return txt


def _render_flow_item(pdf, kind, name, cfg, instance, label, col_w, fill=False):
    """FIELD/TEXT em fluxo datilográfico: segue na linha (PCOL avança);
    envolve p/ margem se não couber; trunca o excedente se maior que a linha.
    Posicionado (tab/location/pos) = absoluto, sem envoltório.
    `fill` = TEXT avulso sem width ocupa o resto da zona (linha própria com
    largura da zona — é o que faz `align` R/C valer); sub-item de TEXTS é
    apertado (inline) e FIELD nunca preenche.
    """
    from ajsystem.core.text import render as _trender
    _x0, right = _flow_zone(pdf)
    _fixed = any(k in cfg for k in ('tab', 'location', 'pos'))
    _fam = None
    if 'font' in cfg or 'cpp' in cfg:
        # Override temporário por item (diretiva intacta): família e/ou pitch.
        from ajsystem.defs.fonts import CPP as _CPP
        _base = getattr(pdf, '_gridfont', None) or {}
        _fam = cfg.get('font', _base.get('family', FONT_FAMILY))
        _c = cfg.get('cpp', _base.get('cpp', 0))
        if _c not in _CPP:
            raise ValueError(f"report '{label}': cpp deve ser 0|1|2|3")
        col_w = 25.4 / _CPP[_c]
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
        lbl = cfg.get('label', name) or ''
        _ff, _fs, _fst = _font_default(pdf)
        _ff = _fam or _ff
        pdf.set_font(_ff, "B", _fs)
        lw = (pdf.get_string_width(lbl + ': ') + 2) if lbl else 0
        _apply_font(pdf, _ff, _fs, _fst)
        vw = pdf.get_string_width(txt or '') + 2
        if _want_wrap(cfg, kind, label):
            # Rótulo na primeira linha (como `cell`), valor quebrando no resto da
            # zona. `FIELD` sempre aperta o valor na largura do texto; aqui ele
            # passa a ocupar a linha, que é o que uma frase precisa.
            if lbl:
                pdf.set_font(_ff, "B", _fs)
                pdf.cell(lw, ROW_CELL, lbl + ': ', new_x="END")
                _apply_font(pdf, _ff, _fs, _fst)
            pdf.multi_cell(_wrap_width(pdf, cfg.get('width')), ROW_CELL, txt,
                           new_x="LMARGIN", new_y="NEXT")
            if txt:
                _mark_content(pdf)
            return
        if not _fixed and pdf.get_x() + lw + vw > right + 0.01 and pdf.get_x() > _x0 + 0.01:
            pdf.ln(ROW_CELL)  # pcol+1>ncol -> pcol=1, prow+=1
            pdf.set_x(_x0)
        if lw + vw > right - _x0:
            txt, vw = _cut_to_fit(pdf, txt, right - _x0 - lw), right - _x0 - lw
        if lbl:
            pdf.set_font(_ff, "B", _fs)
            pdf.cell(lw, ROW_CELL, lbl + ': ', new_x="END")
            _apply_font(pdf, _ff, _fs, _fst)
        pdf.cell(vw, ROW_CELL, txt, new_x="END", new_y="TOP")
        if txt:
            _mark_content(pdf)
    else:  # TEXT
        from ajsystem.core.text import dotted_get as _dg
        txt = _trender(cfg.get('text', ''), lambda k: _dg(instance, k) if instance is not None else None, cfg.get('_fmt_opts'))
        _ff, _fs, _fst = _font_default(pdf)
        _ff = _fam or _ff
        pdf.set_font(_ff, cfg.get('font_style', _fst) or _fst, cfg.get('font_size', _fs))
        if _want_wrap(cfg, kind, label):
            # `wrap`: quebra na zona em vez de cortar a ponta. `multi_cell`
            # ocupa a linha toda, então `align` R/C passa a valer no texto
            # quebrado também — e `_cut_to_fit` some de propósito, que era ele
            # que comia o resto da frase.
            if not _fixed and pdf.get_x() > _x0 + 0.01 and cfg.get('width') is None:
                pdf.set_x(_x0)
            pdf.multi_cell(_wrap_width(pdf, cfg.get('width')), ROW_CELL, txt,
                           align=cfg.get('align', 'L'),
                           new_x="LMARGIN" if not _fixed else "END", new_y="NEXT")
            if txt:
                _mark_content(pdf)
            return
        _w = cfg.get('width')
        if _w is not None:
            if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
                raise ValueError(f"report '{label}': width deve ser cols > 0")
            _w = _w * _col_unit(pdf)
            pdf.set_font(_ff, cfg.get('font_style', _fst) or _fst, cfg.get('font_size', _fs))
        elif fill and not _fixed:
            _w = right - pdf.get_x()
            if pdf.get_string_width(txt or '') + 2 > _w:
                txt = _cut_to_fit(pdf, txt, _w)  # linha própria: trunca na zona
        else:
            _w = pdf.get_string_width(txt or '') + 2
        if not _fixed and pdf.get_x() + _w > right + 0.01 and pdf.get_x() > _x0 + 0.01:
            pdf.ln(ROW_CELL)
            pdf.set_x(_x0)
        if _w > right - _x0:
            txt, _w = _cut_to_fit(pdf, txt, right - _x0), right - _x0
        pdf.cell(_w, ROW_CELL, txt, align=cfg.get('align', 'L'), new_x="END", new_y="TOP")
        if txt:
            _mark_content(pdf)


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
        pdf._gridfont = None
        pdf._ind = None
    col_w = _col_unit(pdf)
    _titulos = 0   # cascata de TITLE desta lista (1º = título, demais = subtítulo)
    for it in items or []:
        kind, name, cfg = _split_item(it, label)
        if kind == 'FIELDS':
            raise ValueError(f"report '{label}': FIELDS deve ser expandido no apply (do_report)")
        if kind == 'FONT':
            if not cfg.get('font') and cfg.get('cpp') is None:
                pdf._gridfont = None  # FONT() nu = restaura o default
            else:
                pdf._gridfont = _resolve_font(cfg, label)
            col_w = _col_unit(pdf)
            continue
        if kind in ('FIELD', 'TEXT', 'LINE', 'BOX', 'CIRCLE', 'MEMO', 'LF', 'TITLE') \
                and cfg.get('when') is not None:
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
                _mark_content(pdf)
            continue
        if kind == 'POS':
            _c, _r = _resolve_tokens(pdf, cfg.get('values'), label)
            for _v in (_c, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)):
                    raise ValueError(f"report '{label}': POS exige [col, lin]")
            pdf.set_xy(pdf.l_margin + _c * col_w, pdf.t_margin + _r * ROW_CELL)
            continue
        if kind == 'TEXTS':
            for _sub in cfg.get('items', []):
                if isinstance(_sub, str):
                    _tcfg = {'text': _sub}
                elif isinstance(_sub, dict) and set(_sub) == {'TEXT'} and isinstance(_sub.get('TEXT'), dict):
                    _tcfg = _sub['TEXT']
                elif isinstance(_sub, tuple):
                    if len(_sub) != 2 or not isinstance(_sub[1], str):
                        raise ValueError(f"report '{label}': par TEXTS deve ser (texto|cfg, when)")
                    if isinstance(_sub[0], str):
                        _tcfg = {'text': _sub[0], 'when': _sub[1]}
                    elif isinstance(_sub[0], dict) and isinstance(_sub[0].get('text'), str):
                        _tcfg = dict(_sub[0])
                        _tcfg['when'] = _sub[1]
                    else:
                        raise ValueError(f"report '{label}': par TEXTS deve ser (texto|cfg, when)")
                elif isinstance(_sub, dict) and isinstance(_sub.get('text'), str):
                    _tcfg = {k: v for k, v in _sub.items() if k != 'text'}
                    _tcfg['text'] = _sub['text']
                else:
                    raise ValueError(f"report '{label}': TEXTS aceita texto, (texto, when) ou {{'text': ...}}")
                _when = _tcfg.get('when')
                if _when is not None:
                    from ajsystem.core.text import eval_when as _ew
                    if not _ew(instance, _when):
                        continue
                _place_item(pdf, 'TEXT', 'text', _tcfg, label, line=False)
                _render_flow_item(pdf, 'TEXT', 'text', _tcfg, instance, label, col_w)
            continue
        if kind in ('TITLE', 'TITLES'):
            # Título no corpo é o MESMO desenho do header (mesmo helper, mesma
            # cascata), com os defaults vindos das constantes: no corpo não há
            # `header.title_font_size` para consultar. A cascata é desta lista
            # de items — cada `before`/`after` recomeça, como no header.
            # `tab` não existe aqui (as paradas são do header), então é recusado
            # nomeando a prop em vez de ancorar no lugar errado sem avisar.
            if 'tab' in cfg:
                raise ValueError(
                    f"report '{label}': TITLE no corpo não aceita 'tab' — "
                    f"use 'location'/'pos'")
            if kind == 'TITLE':
                _titulos = _draw_titulo(pdf, cfg, None, label, instance=instance,
                                        drawn=_titulos, title_size=FONT_TITLE,
                                        title_style='B', sub_size=FONT_SUBTITLE,
                                        sub_style='')
            else:
                for _sub in cfg.get('items') or []:
                    _k, _n, _cfg = _split_item(_sub, label)
                    if _k != 'TITLE':
                        raise ValueError(f"report '{label}': TITLES aceita só TITLE, veio {_k!r}")
                    if 'tab' in _cfg:
                        raise ValueError(
                            f"report '{label}': TITLE no corpo não aceita 'tab' — "
                            f"use 'location'/'pos'")
                    _titulos = _draw_titulo(pdf, _cfg, None, label, instance=instance,
                                            drawn=_titulos, title_size=FONT_TITLE,
                                            title_style='B', sub_size=FONT_SUBTITLE,
                                            sub_style='')
            continue
        if kind == 'MEMO':
            from ajsystem.core.text import render as _mrender, dotted_get as _mdg
            _campo = cfg.get('field')
            if _campo:
                # FIELD com medida: o valor vem resolvido — `function` (que já
                # traduz LIST pelo catálogo, vindo da Entity ou do override
                # `options`) e a máscara. É o mesmo passo do item FIELD.
                if instance is None:
                    raise ValueError(
                        f"report '{label}': memo '{_campo}' exige instância (documento)")
                _fn, _fmt = cfg.get('function'), cfg.get('format')
                try:
                    _val = _fn(instance) if callable(_fn) else _mdg(instance, _campo)
                except Exception:
                    _val = None
                _txt = _format_cell_value(_val, _fmt if _fmt is not None
                                          else cfg.get('mask'))
            else:
                # TEMPLATE (`'Prezado {fornecedor.nome}, ...'`): avaliador de
                # `TEXT`, sem label nem catálogo do report — a mesma distinção
                # que separa FIELD de TEXT.
                _txt = _mrender(cfg.get('text', ''),
                                lambda k: _mdg(instance, k) if instance is not None else None,
                                cfg.get('_fmt_opts'))
            _ff, _fs, _fst = _font_default(pdf)
            _size = cfg.get('font_size', _fs)
            _style = cfg.get('font_style', _fst) or _fst
            _x0, _right = _flow_zone(pdf)
            # largura do bloco, sem passar da zona; centralizado na área livre.
            # `IND` resolveria o mesmo recuo, mas abriria uma zona que vaza para
            # os itens seguintes e depende de ordem — aqui a largura é do item.
            _w = min(cfg.get('width', 0) * _col_unit(pdf), _right - _x0)
            _bx = _x0 + (_right - _x0 - _w) / 2
            # `recuo` (cols) afasta só a PRIMEIRA linha, dentro do bloco: a
            # centralização acima não muda e `width` continua medindo o bloco
            # inteiro. A 1ª linha quebra na medida `w - recuo`, o que é
            # literalmente `spaces(recuo) + texto` sem o justifiable esticar o
            # recuo. O parse já recusa `recuo >= width`, então aqui dá p/ usá-lo.
            _recuo = cfg.get('recuo', 0) * _col_unit(pdf)
            _lbl = cfg.get('label') or ''
            if _lbl:
                pdf.set_font(_ff, 'B', _size)
                pdf.set_x(_bx)
                pdf.cell(pdf.get_string_width(_lbl) + 2, ROW_CELL, _lbl,
                         new_x="END", new_y="NEXT")
            # A fonte ANTES de medir: `_wrap_linhas` decide onde quebrar pelo
            # `get_string_width`, e medir na fonte anterior produz linhas mais
            # largas que o bloco (o bloco saía com 154mm num espaço de 141mm).
            pdf.set_font(_ff, _style, _size)
            _linhas = _wrap_linhas(pdf, _txt, _w, first=_w - _recuo) if _txt else []
            if _linhas:
                _draw_bloco(pdf, _linhas, _bx, _w, ROW_CELL, _ff, _size, _style,
                            cfg.get('align', MEMO_ALIGN), _recuo)
                pdf.set_x(_flow_zone(pdf)[0])
            continue
        if kind == 'CR':
            pdf.set_x(_flow_zone(pdf)[0])  # volta à 1ª coluna, mesma linha
            continue
        if kind == 'LF':
            _n = cfg.get('lines', 1)
            if isinstance(_n, bool) or not isinstance(_n, (int, float)) or _n < 1:
                raise ValueError(f"report '{label}': LF exige lines >= 1")
            pdf.ln(_n * ROW_CELL)
            pdf.set_x(_flow_zone(pdf)[0])
            continue
        if kind == 'FF':
            if getattr(pdf, '_in_header', False):
                raise ValueError(f"report '{label}': FF só no corpo (header repete por página)")
            pdf.add_page()
            continue
        if kind == 'IND':
            _vals = cfg.get('values') or []
            if not _vals:
                pdf._ind = None  # IND() nu = restaura (margens+área útil)
                continue
            if len(list(_vals)) != 2:
                raise ValueError(f"report '{label}': IND exige [l, r]")
            _l, _r = _resolve_tokens(pdf, list(_vals), label)
            for _v in (_l, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)) or _v < 0:
                    raise ValueError(f"report '{label}': IND exige [l, r] não-negativos")
            _ncol = _usable_cols(pdf)
            if not (_l < _r) or _r > _ncol + 0.01:
                raise ValueError(f"report '{label}': IND [{_l}, {_r}] fora da área (ncol={_ncol:.1f})")
            pdf._ind = [_l, _r]
            continue
        rb, ra = int(cfg.get('rows_before', 0) or 0), int(cfg.get('rows_after', 0) or 0)
        if rb:
            pdf.ln(rb * ROW_CELL)
            pdf.set_x(_flow_zone(pdf)[0])
        _place_item(pdf, kind, name, cfg, label)
        if kind in ('FIELD', 'TEXT'):
            _render_flow_item(pdf, kind, name, cfg, instance, label, col_w, fill=True)
        elif kind == 'IMAGE':
            src = cfg.get('path') or (getattr(instance, cfg.get('field', name), None) if instance is not None else None)
            if not src:
                raise ValueError(f"report '{label}': IMAGE sem path/field")
            from flask import current_app
            import os as _os
            path = src if _os.path.isabs(str(src)) else _os.path.join(current_app.root_path, str(src))
            x, y, w, hh = _image_box(pdf, cfg.get('location'), path)
            pdf.image(path, x=x, y=y, w=w, h=hh)
            _mark_content(pdf)
        else:  # LINE / BOX / CIRCLE
            g = _gmm(_gloc(kind, _elem_location(pdf, kind, cfg, label)),
                     ROW_CELL, col_w)
            ox, oy = pdf.l_margin, pdf.t_margin
            if kind == 'LINE':
                if g.get('ponto'):
                    # Extensão (0,0): um `line` degenerado emitiria um
                    # subcaminho de comprimento zero e não pintaria nada —
                    # o ponto vira disco. Raio = 1/8 da coluna, para acompanhar
                    # o pitch da fonte vigente (col_w = 25.4/cpp).
                    pdf.circle(ox + g['x1'], oy + g['y1'], col_w / 8)
                else:
                    pdf.line(ox + g['x1'], oy + g['y1'], ox + g['x2'], oy + g['y2'])
            elif kind == 'BOX':
                pdf.rect(ox + g['x'], oy + g['y'], g['w'], g['h'])
            else:
                pdf.ellipse(ox + g['x'] - g['rx'], oy + g['y'] - g['ry'],
                            2 * g['rx'], 2 * g['ry'])
            _mark_content(pdf)
            if kind == 'LINE':
                # A régua ocupa uma linha: o cursor desce e volta ao início da
                # zona, para o próximo item não colidir com ela.
                pdf.ln(ROW_CELL)
                pdf.set_x(_flow_zone(pdf)[0])
        if ra:
            pdf.ln(ra * ROW_CELL)
            pdf.set_x(_flow_zone(pdf)[0])


def _margin_mm(v, label):
    """Margem em mm ou {'cols': n} (cols draft 2.54mm). Congelada aqui: troca
    de fonte nunca recalcula margem."""
    from ajsystem.defs.fonts import DRAFT_COL_MM
    if isinstance(v, dict):
        if set(v) != {'cols'}:
            raise ValueError(f"report '{label}': margem dict deve ser {{'cols': n}}")
        n = v['cols']
        if isinstance(n, bool) or not isinstance(n, (int, float)) or n < 0:
            raise ValueError(f"report '{label}': cols deve ser número >= 0")
        return n * DRAFT_COL_MM
    return v


def gerar_pdf_relatorio(report: Report, data: list = None, logo_path: str = None,
                        instance=None, title_substitutions: dict = None) -> DocPDFReport:
    """Gera PDF genérico a partir de um Report."""
    data = data or []
    _ml = _margin_mm(report.margin_left, report.label)
    _mt = _margin_mm(report.margin_top, report.label)
    _mr = _margin_mm(report.margin_right, report.label)
    _mb = _margin_mm(report.margin_bottom, report.label)

    pdf = DocPDFReport(report)
    pdf.set_auto_page_break(auto=report.auto_page_break, margin=_mb)
    pdf.set_margins(_ml, _mt, _mr)

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
        _before = _lines_de_callable(_before, instance, 'body.before',
                                     report.label if report else '')
    if _before:
        _render_table_lines(pdf, _before, instance, prop='body.before', report=report)

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
        _after = _lines_de_callable(_after, instance, 'body.after',
                                    report.label if report else '')
    if _after:
        _render_table_lines(pdf, _after, instance, prop='body.after', report=report)
    if tbl.after and instance:
        if isinstance(tbl.after, list):
            pdf.ln(GAP_AFTER_TABLE)  # respiro pós-régua, igual ao ramo string
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
