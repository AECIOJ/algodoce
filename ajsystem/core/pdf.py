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
    'title': {'label': None, 'align': 'C', 'style': 'B'},
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
    title_style: str = 'B'
    title_align: str = 'C'
    subtitle: Optional[str] = None
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


def _build_header(report: Report) -> '_ReportHeader':
    if isinstance(report.header, list):
        # Forma lista: header=[...] (ReportItem). Defaults + raw p/ render.
        return _ReportHeader(
            show_logo=False,
            logo_path=None,
            title_style=_HEADER_DEFAULTS['title'].get('style', 'B'),
            title_align=_HEADER_DEFAULTS['title'].get('align', 'C'),
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
    title_style = title_cfg.get('style', h.get('title_style', 'B'))
    title_align = title_cfg.get('align', h.get('title_align', 'C'))

    # Subtítulo: dict, str ou None
    sub_cfg = h.get('subtitle')
    if isinstance(sub_cfg, dict):
        subtitle = sub_cfg.get('label')
        subtitle_align = sub_cfg.get('align', h.get('subtitle_align', 'C'))
    else:
        subtitle = sub_cfg
        subtitle_align = h.get('subtitle_align', 'C')

    return _ReportHeader(
        show_logo=show_logo,
        logo_path=h.get('logo_path'),
        logo_width=h.get('logo_width'),
        logo_height=0,
        logo_align=logo_align,
        logo_location=logo_location,
        title=title,
        title_style=title_style,
        title_align=title_align,
        subtitle=subtitle,
        subtitle_align=subtitle_align,
        fields=h.get('fields'),
        field_columns=h.get('field_columns', 2),
        on_each_page=h.get('on_each_page', True),
        layout=h.get('layout', 'centered'),
        line=bool(h.get('line', False)),
    )


def _draw_titulo(pdf, cfg, h, label='', instance=None, drawn=0):
    """Desenha 1 TITLE. Devolve quantos títulos já foram desenhados (o próprio
    contador, quando o `when` pula).

    **A cascata é por POSIÇÃO, e é de estilo — não de corpo:**

        1º  CPI 5 (expandido) + bold   -> 2x a largura do corpo
        2º  CPI 10 (normal)    + bold
        3º+ CPI 10 (normal)

    Antes o 1º era `FONT_TITLE` (16pt) e o resto `FONT_SUBTITLE` (10pt), e o
    corpo solto com `size * 0.6` de altura — o título ocupava quase duas linhas
    e a grade vertical não sabia disso. Agora o corpo é `60/LPI` para TUDO, e o
    que separa o 1º do resto é o CPI: o expandido dobra a largura do glifo, e
    como a grade estica o glifo para a célula, centralizar continua exato.

    `style`/`cpi` declarados mudam o traço e a célula sem mudar a POSIÇÃO — o
    1º continua sendo o 1º, que é o que separa "declarar estilo" de "virar
    subtítulo".
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
        # Bloco: volta ao INÍCIO DA ZONA (não da margem), e o `w` abaixo é a
        # sobra dela. Com o logo encolhendo a zona, voltar à margem punha o
        # título dentro da imagem.
        pdf.set_x(_flow_zone(pdf)[0])
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
    if 'font_size' in cfg:
        raise ValueError(
            f"report '{label}': font_size saiu — o corpo é derivado do LPI "
            f"(60/LPI) e vale para todo o documento; use 'cpi' para a largura "
            f"da célula e 'style' para o traço")
    # Cascata por POSIÇÃO e de estilo, não de corpo: 1º = expandido + negrito
    # (2x a largura do corpo), 2º = normal + negrito, 3º+ = normal. O `flags`
    # é o modificador da matriz, então o 1º acompanha o base vigente em vez de
    # ser um número cravado.
    _cascata = {'flags': 'E' if first else '', 'style': 'B' if first else ''}
    if 'cpi' in cfg:
        raise ValueError(
            f"report '{label}': 'cpi' no TITLE não combina com 'flags' — "
            f"a cascata escolhe a largura pelo flags ({_cascata['flags'] or 'normal'})")
    cpi_t = _cpi_de(pdf, {'flags': cfg.get('flags', _cascata['flags'])})
    style = _validate_style(cfg.get('style', _cascata['style']), label, 'TITLE')
    if cfg.get('options') is not None and not isinstance(cfg['options'], dict):
        raise ValueError(
            f"report '{label}': 'options' do TITLE deve ser dict "
            f"(catálogo {{codigo: rótulo}}), veio {type(cfg['options']).__name__}")
    # TITLE sempre centralizado por default; outro align só se declarado.
    align = cfg.get('align', 'C')
    # A face (família + estilo + corpo + alongamento) ANTES de qualquer
    # medição: `get_string_width` já conta o alongamento, e medir antes de
    # esticar daria a largura do glifo cru e centralizaria errado.
    _apply_face(pdf, style, cpi=cpi_t)
    _w = cfg.get('width')
    if _w is not None:
        if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
            raise ValueError(f"report '{label}': width deve ser cols > 0")
        _w = _w * _col_unit(pdf)
    else:
        # Só o resto da ZONA — `w = 0` iria até a margem direita e centralizaria
        # o título no espaço inteiro, atravessando a imagem.
        _w = _flow_zone(pdf)[1] - pdf.get_x()
    # Altura = 1 LINHA da grade. O título não tem corpo maior, então também não
    # ocupa mais que uma linha: expandido é na HORIZONTAL (o CPI), e a altura
    # continua sendo a do corpo.
    pdf.cell(_w, _row_unit(pdf), txt or '', align=align, new_x="LMARGIN", new_y="NEXT")
    _mark_content(pdf)
    # O avanço é `rows_after` e o padrão é 1 LINHA — não mais um gap em mm.
    # `rows_before`/`rows_after` significam avanço de linha, e o título era a
    # única coisa que ainda espaçava em milímetros (4mm no 1º, 3mm nos demais).
    # Declarar `rows_after: N` maior afasta mais; `0` cola no próximo item.
    _ra = cfg.get('rows_after', 1)
    if isinstance(_ra, bool) or not isinstance(_ra, (int, float)) or _ra < 0:
        raise ValueError(
            f"report '{label}': rows_after do TITLE deve ser número >= 0, veio {_ra!r}")
    if _ra:
        pdf.ln(_ra * _row_unit(pdf))
    return drawn + 1


def _render_header_items(self, h):
    """Header em forma lista: LOGO/TITLE (cascata)/FIELD/TEXT/IMAGE/formas."""
    from ajsystem.defs.report import parse_report_item
    from ajsystem.core.text import render as _trender
    label = self._report.label if getattr(self, '_report', None) else ''
    from ajsystem.defs.fonts import (CPI_DEFAULT, LPI_DEFAULT, cpi as _cpi_norm,
                                     lpi as _lpi_norm)
    items = [parse_report_item(it, label) for it in (h.raw_header or [])]
    self._tabs = None
    self._cpi = CPI_DEFAULT
    self._flags = ''
    self._lpi = LPI_DEFAULT
    self._ind = None
    self._logo_zone = None
    titles = 0
    for item in items:
        cfg = item.config
        if item.kind == 'CPI':
            self._cpi = _cpi_norm(cfg['cpi']) if 'cpi' in cfg else CPI_DEFAULT
            self._flags = cfg.get('flags', '')
            continue
        if item.kind == 'LPI':
            self._lpi = _lpi_norm(cfg['lpi']) if 'lpi' in cfg else LPI_DEFAULT
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
                        self.t_margin + _r * _row_unit(self))
            continue
        if item.kind == 'LOGO':
            logo = h.logo_path
            if not logo:
                continue
            loc = cfg.get('location', ['C', 4])
            x, y, w, hh = _image_box(self, loc, logo)
            self.image(logo, x=x, y=y, w=w, h=hh)
            # O logo ENCOLHE A ZONA pelo espaço vago ao lado da imagem, para o
            # texto que divide a faixa com ele: em 'L' a zona começa na borda
            # direita da figura, em 'R' termina na borda esquerda. A faixa vale
            # enquanto o cursor estiver nestas linhas (`_zone_cols`), e 'C' não
            # indenta nada — sobra igual dos dois lados.
            _anc = (loc[0] if isinstance(loc, (list, tuple)) and loc else 'C')
            col_w = _col_unit(self)
            _c1 = (x - self.l_margin) / col_w
            _c2 = (x + w - self.l_margin) / col_w
            self._logo_zone = {
                'l': _c2 if _anc == 'L' else None,
                'r': _c1 if _anc == 'R' else None,
                'y1': y, 'y2': y + hh,
            }
            # Cursor p/ o fim da caixa: o próximo item ancora a partir daqui; sem
            # âncora, o bloco volta ao início da ZONA.
            self.set_xy(x + w, y + hh)
            _mark_content(self)
        elif item.kind == 'TITLE':
            titles = _draw_titulo(self, cfg, h, label, instance=self._instance, drawn=titles)
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
                titles = _draw_titulo(self, _cfg, h, label, instance=self._instance, drawn=titles)
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
    )


class DocPDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(FOOTER_Y)
        _apply_face(self, 'I')
        self.cell(0, _row_unit(self), f"Página {self.page_no()}/{{nb}}", align="C")


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

    def output(self, *args, **kwargs):
        """Envolve `output` para calar o `fontTools.subset`.

        O subsetter descarta a tabela `TTFA` (metadado do FontLab que o Hack
        traz) e avisa em WARNING — 4 linhas por PDF sobre algo que o autor do
        report não pediu, e que aparece no meio dos logs do app. Silencia só
        esse logger e só durante o `output`, que é onde o subsetting acontece
        (não no `add_font`).
        """
        import logging
        _log = logging.getLogger('fontTools.subset')
        _antes = _log.level
        # Sem este `if`: o logger nasce em NOTSET (0) e herda do pai, e `0 > 30`
        # é falso — que é justamente o caso comum, e o aviso vazava.
        _log.setLevel(logging.ERROR)
        try:
            return super().output(*args, **kwargs)
        finally:
            _log.setLevel(_antes)

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
            _apply_face(self, h.title_style, cpi=5)
            self.cell(right_w, _row_unit(self), title, align='C',
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
            _apply_face(self, h.title_style, cpi=5)
            self.cell(0, _row_unit(self), title, align=h.title_align,
                      new_x="LMARGIN", new_y="NEXT")
            self.ln(_row_unit(self))  # título sempre deixa a PRÓXIMA linha

        # Subtitle
        if h.subtitle:
            _apply_face(self)
            self.cell(0, _row_unit(self), h.subtitle,
                      align=h.subtitle_align, new_x="LMARGIN", new_y="NEXT")
            self.ln(_row_unit(self))  # idem para o subtítulo

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
        row_h = _row_unit(self)
        col = 0
        row = 0
        for rf in parsed:
            x = x_start + col * col_w
            y = y0 + row * row_h
            # Label (bold)
            self.set_xy(x, y)
            _apply_face(self, 'B')
            lbl = (rf.label or rf.field or '') + ':'
            self.cell(col_w * 0.4, row_h, lbl, new_x="END")
            # Value
            _apply_face(self)
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
            _apply_face(self, 'I')
            self.cell(0, _row_unit(self), f.separator.join(parts), align=f.align)


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

# ── Medidas fixas do motor ─────────────────────────────────────────────────
# As alturas de LINHA (`ROW_CELL`/`ROW_HEAD`/`ROW_FOOT`/`ROW_GROUP_*`/`LINE_TALL`)
# e os corpos de fonte (`FONT_*`) saíram: a linha é `25,4/LPI` e o corpo é
# `60/LPI`, ambos derivados (ver `_row_unit`/`_size`). Sobrou só o que é
# respiro em mm/cols, que não é altura de linha.
FONT_FAMILY = "Helvetica"          # fallback para texto solto sem grade
GAP_LABEL = 1          # respiro rótulo→valor, em COLS
GAP_HEAD_FIELDS = 4    # após fields do cabeçalho
GAP_TEXT_LINE = 2      # antes de cada linha avulsa
GAP_TEXT_EMPTY = 8     # linha avulsa vazia
GAP_HEAD_FIELDS_SINGLE = 4  # após fields quando cabeçalho é só da 1ª página
INDENT_GROUP_TITLE = 2   # recuo título de grupo (mm)
INDENT_GROUP_LINE = 6    # recuo linha de grupo (mm)
INDENT_PER_LEVEL = 4     # recuo adicional por nível (mm)
FOOTER_Y = -15           # recuo do rodapé de página
GAP_TITLE_SIDE = 2      # após título no layout logo_left
GAP_AFTER_TABLE = 4     # antes do texto after da tabela
GAP_TEXTS = 4           # antes de cada texto avulso


PAPER_FIT_MSG = ('Largura do papel insuficiente para relatorio. '
                 'Mude orientação ou tipo de papel.')


def _calc_col_widths(pdf, cols, cpi=10):
    """Converte widths (ch) → mm no pitch nominal (tabela sempre draft).

    - Colunas com `width` (ch) → mm exato em 25.4/CPI;
    - Sem nenhuma width → divisão igual;
    - Com widths parciais → restante dividido entre as sem width;
    - Todas com width → bloco centrado no disponível.
    """
    from ajsystem.defs.fonts import col_mm
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    unit = col_mm(cpi)
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
    """Auto-fit pela escada da grade: primeiro CPI que cabe (total + piso em
    caracteres). Tabela é sempre draft; font/cpi/lpi dentro dela = fail-fast.

    A escada é {10, 17, 20} — N, S, C. O `E` (5) fica de fora de propósito: é o
    expandido do título, e uma tabela que auto-fitasse nele sairia com 5,08mm
    por caractere."""
    from ajsystem.defs.fonts import TABLE_LADDER, col_mm
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    for cpi in TABLE_LADDER:
        col_widths, total_w, x_start = _calc_col_widths(pdf, cols, cpi)
        _floor = MIN_COL_CHARS * col_mm(cpi)
        if total_w <= avail_w + 0.01 and all(w + 0.01 >= _floor for w in col_widths):
            return col_widths, total_w, x_start, cpi
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
    _apply_face(pdf, 'B')
    row_h = _row_unit(pdf)
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
    _apply_face(pdf)
    row_h = _row_unit(pdf)
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
                pdf.ln(_row_unit(pdf))
                _stayed = False
            if _check_page_break(pdf, _row_unit(pdf)):
                _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
            _draw_hline(pdf, x_start, total_w)
            # NÃO avança: a régua no `extend` é DIVISOR, não linha. Ela nasce no
            # topo da faixa e a linha seguinte se apoia nela — a régua ocupa o
            # lugar da faixa em branco que o `ln(_row_unit(pdf))` custaria, que era o
            # jeito de o autor bancar um separador e ganhar uma linha vazia.
            continue
        if isinstance(it, str):
            if it not in ('LF', 'CR'):
                raise ValueError(
                    f"report '{label}': extend aceita tupla, LINE(), LF ou CR "
                    f"(a régua é LINE(), não a string 'LINE')")
            if it == 'LF':
                pdf.ln(_row_unit(pdf))
            else:
                pdf.set_x(x_start)
            _stayed = False
            continue
        if not (isinstance(it, tuple) and 2 <= len(it) <= 3):
            raise ValueError(f"report '{label}': extend exige (col, texto[, props])")
        _col, _text = it[0], it[1]
        _props = dict(it[2]) if len(it) == 3 else {}
        for _fk in ('font', 'cpi', 'flags', 'lpi', 'font_size'):
            if _fk in _props:
                raise ValueError(
                    f"report '{label}': '{_fk}' não vale em tabela (a grade da "
                    f"tabela é dela; a fonte é do report)")
        if _props.get('style') not in (None, '', 'B', 'I', 'BI'):
            raise ValueError(f"report '{label}': style em tabela: ''|B|I|BI")
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
        if _check_page_break(pdf, _row_unit(pdf)):
            _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=False)
        _fo = _props.get('_fmt_opts') or {}
        _m = _re.fullmatch(r'{([\w.]+)}', (_text or '').strip())
        if _m and _props.get('format') is None and _fmt_dflt is not None:
            # Placeholder puro: herda formatação da coluna.
            _txt = _format_cell_value(_dg(instance, _m.group(1)) if instance is not None else None, _fmt_dflt)
        else:
            _txt = _trender(_text, lambda k: _dg(instance, k) if instance is not None else None, _fo)
        _apply_face(pdf, _props.get('style', ''))
        pdf.set_x(_x)
        _last_col = _b if isinstance(_col, list) else _col
        _stay = _last_col < n
        pdf.cell(_w, _row_unit(pdf), _txt, align=_props.get('align', _align_dflt),
                 new_x="END" if _stay else "LMARGIN",
                 new_y="TOP" if _stay else "NEXT")
        _stayed = _stay
        if _txt:
            _mark_content(pdf)
    if _stayed:
        pdf.ln(_row_unit(pdf))


def _render_footer_row(pdf, cols, col_widths, totals, agg_values, x_start, total_w, close=True):
    """Linha de total geral: rótulo nas SPAN primeiras + func por coluna agg."""
    _draw_hline(pdf, x_start, total_w)  # régua antes (interna, sempre)
    _apply_face(pdf, 'B')
    span = totals.get('span')
    nspan = len(cols) - 1 if span is None else min(span, len(cols) - 1)
    label_w = sum(col_widths[:nspan])
    pdf.set_x(x_start)
    pdf.cell(label_w, _row_unit(pdf), totals.get('label', TOTALS_DEFAULT_LABEL),
             border=0, align=totals.get('align', 'C'))
    _positions = [i for i, col in enumerate(cols) if i >= nspan and col.agg]
    if not _positions:
        pdf.set_x(x_start + label_w)
        pdf.cell(total_w - label_w, _row_unit(pdf), '', border=0,
                 new_x="LMARGIN", new_y="NEXT")
    for i in _positions:
        col = cols[i]
        v = _agg_apply(col.agg, agg_values.get(col.field))
        pdf.set_x(x_start + sum(col_widths[:i]))
        pdf.cell(col_widths[i], _row_unit(pdf), _format_cell_value(v, col.format),
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
    indent = INDENT_GROUP_TITLE if pos == 2 else INDENT_GROUP_LINE
    height = _row_unit(pdf) if pos == 2 else _row_unit(pdf)
    _apply_face(pdf, style)
    pdf.set_x(xs + indent)
    pdf.cell(tw - indent, height, txt, border=0,
             new_x="LMARGIN", new_y="NEXT")
    _mark_content(pdf)


def _render_group_line(pdf, g, val, xs, tw, row=None):
    """Linha `pos=1` — interna à tabela, texto corrido na largura da tabela."""
    txt = apply_transform(_group_title(g, val, row=row), g.get('transform'))
    style = 'B' if g.get('bold', True) else ''
    _apply_face(pdf, style)
    indent = max(1, int(g.get('left', 1) or 1)) * INDENT_PER_LEVEL
    height = _row_unit(pdf)
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
    _apply_face(pdf, 'B')
    label = totals.get('label', 'Sub-Total')
    if label and row is not None and ('{' in label):
        label = _group_title({**g, 'text': label}, None, row=row)
    span = totals.get('span')
    nspan = len(cols) - 1 if span is None else min(span, len(cols) - 1)
    label_w = sum(cw[:nspan])
    pdf.set_x(xs)
    pdf.cell(label_w, _row_unit(pdf), label, border=0, align=totals.get('align', 'C'))
    _positions = [i for i, col in enumerate(cols) if i >= nspan and col.agg]
    if not _positions:
        pdf.set_x(xs + label_w)
        pdf.cell(sum(cw[nspan:]), _row_unit(pdf), '', border=0,
                 new_x="LMARGIN", new_y="NEXT")
        return
    for i in _positions:
        col = cols[i]
        v = _agg_apply(col.agg, acc.get(col.field))
        pdf.set_x(xs + sum(cw[:i]))
        pdf.cell(cw[i], _row_unit(pdf), _format_cell_value(v, col.format),
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
                        pdf.ln(lines_after * _row_unit(pdf))
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
    col_widths, total_w, x_start, _cpi = _fit_table(pdf, cols, label)
    # Bordas reais p/ LTB/RTB em mm (última tabela vence; sem tabela = área
    # útil). Guarda em mm e converte na resolução: âncora/fluxo/IND vivem na
    # unidade da fonte corrente (`_col_unit`), que muda com FONT — gravar já
    # em cols do pitch da tabela brigava com o `ncol` da validação do IND.
    pdf._table_bounds = [x_start, x_start + total_w]
    pdf._table_cpi = _cpi

    # Dados — grupos por mudança de valor (specs normalizadas em _apply_entity)
    agg_values = {c.field: [] for c in cols if c.agg}
    header_h = _row_unit(pdf) + _row_unit(pdf)
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
        footer_h = _row_unit(pdf)
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


def _draw_bloco(pdf, linhas, x, w, h, style, align, recuo=0.0,
                prefixo=('', '', 0.0)):
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

    `prefixo` = `(texto, estilo, largura_mm)` do rótulo, que ocupa o COMEÇO da
    1ª linha (é o `label` do `MEMO`). A largura vem pronta do caller porque é o
    mesmo número que a quebra usou em `first` — recalcular aqui seria a chance
    de a 1ª linha caber na conta e não no desenho. A borda direita da 1ª linha
    continua em `x + w`: ela perde o prefixo da medida E ganha o prefixo na
    posição. `C`/`R` alinham o CONJUNTO (rótulo + texto), senão o texto
    centralizado empurraria para fora do rótulo.
    """
    espaco = pdf.get_string_width(' ')
    _ptxt, _pstyle, _pw = prefixo if prefixo else ('', '', 0.0)
    n_linhas = len(linhas)
    for i, ln in enumerate(linhas):
        _check_page_break(pdf, h)
        _apply_face(pdf, style)
        _rec = recuo if i == 0 else 0.0
        pref_w = _pw if (i == 0 and _ptxt) else 0.0
        lx = x + _rec
        lw_m = w - _rec - pref_w
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
            x_linha = lx + (w - _rec - (pref_w + lw)) / 2
        elif align == 'R':
            x_linha = lx + (w - _rec - (pref_w + lw))
        else:
            x_linha = lx
        if i == 0 and _ptxt:
            # o rótulo sai na fonte DELE; o texto começa depois dele
            _apply_face(pdf, _pstyle)
            pdf.set_x(max(x_linha, 0))
            pdf.cell(pref_w, h, _ptxt, new_x='END', new_y='TOP')
            _apply_face(pdf, style)
            x_linha = max(x_linha, 0) + pref_w
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
        style = line.get('style', '')
        align = line.get('align', 'L')
        w = line.get('width', 0)
        if not text and w == 0:
            pdf.ln(GAP_TEXT_EMPTY)
            continue
        pdf.ln(GAP_TEXT_LINE)
        _apply_face(pdf, style)
        if _want_wrap(line, prop):
            # `cell` não quebra (fpdf2): o texto vaza para fora da página e a
            # ponta some. `multi_cell` quebra na largura da zona e cresce, que
            # é o que uma frase precisa.
            pdf.multi_cell(w or _wrap_width(pdf), _row_unit(pdf), text, align=align,
                           new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(w, _row_unit(pdf), text, align=align, new_x="LMARGIN", new_y="NEXT")
        if text:
            _mark_content(pdf)


# Props que fazem uma entrada ser LINHA DE TEXTO e não item. Fechado de
# propósito: `{'text': 'linha'}` e `{'campo': {...}}` são a mesma forma para o
# `_split_item` (dict de uma chave), e sem esta lista o texto mais comum do
# report viraria FIELD chamado `text`.
_TEXT_LINE_KEYS = frozenset(('text', 'style', 'cpi', 'align',
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
    from ajsystem.defs.report import _CursorExpr as _CE
    if isinstance(it, _CE):
        # `PCOL(n)`/`PROW(n)` solto: DIRETIVA de cursor. Dentro de TABS/
        # location o mesmo objeto é valor — quem resolve é `_resolve_tokens`.
        return (it.base, it.base, {'offset': it.offset})
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
                    # Já normalizado (`parse_report_item` entregou
                    # `{'values': [...]}`) volta como está: é o caminho do
                    # header, que delega o item desconhecido para cá.
                    if isinstance(v, dict) and set(v) == {'values'}:
                        return (k, k, {'values': list(v['values'])})
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
        norm = _gloc('IMAGE', _ra(anchor, lines, iw, ih, _row_unit(pdf), col_w, area_cols))
    g = _gmm(norm, _row_unit(pdf), col_w)
    return pdf.l_margin + g['x'], pdf.t_margin + g['y'], g['w'], g['h']


def _cpi(pdf):
    """BASE do CPI vigente (10 Pica · 12 Elite · 15 Micron)."""
    from ajsystem.defs.fonts import CPI_DEFAULT
    return getattr(pdf, '_cpi', CPI_DEFAULT)


def _flags(pdf):
    """Modificadores vigentes (`''` | `'E'` | `'C'` | `'EC'`)."""
    return getattr(pdf, '_flags', '')


def _cpi_de(pdf, cfg=None):
    """CPI FINAL do desenho: o valor que a coluna vai medir.

    `cfg` é o cfg do item — quando ele declara `cpi`/`flags`, vale só para ele;
    senão vale o do fluxo. O valor derivado nunca é declarado: sai de
    `cpi_final(base, flags)`, que é onde a matriz de impressora mora.
    """
    from ajsystem.defs.fonts import cpi_final, flags as _flags_norm
    _base, _fl = _cpi(pdf), _flags(pdf)
    if cfg:
        if 'cpi' in cfg:
            from ajsystem.defs.fonts import cpi as _cpi_norm
            _base = _cpi_norm(cfg['cpi'])
        if 'flags' in cfg:
            _fl = _flags_norm(cfg['flags'])
    return cpi_final(_base, _fl)


def _lpi(pdf):
    """LPI vigente (linhas/pol). Só diretiva `LPI(n)` mexe — nunca prop de item,
    porque um item com LPI próprio desalinha a grade vertical e o PROW(n) passa
    a ler a linha errada."""
    from ajsystem.defs.fonts import LPI_DEFAULT
    return getattr(pdf, '_lpi', LPI_DEFAULT)


def _col_unit(pdf, cfg=None):
    """Largura da COLUNA em mm: `25,4 / CPI` (o CPI **final** do desenho).

    É a grade, não a fonte: o glifo é esticado para ocupar exatamente isto, e
    por isso trocar de fonte não move nada. Antes isto era `get_string_width('0')`
    sem FONT (1,7653mm) e `25,4/cpp` com — duas contas para a mesma coluna, e a
    que valia dependia de haver diretiva de fonte no fluxo.
    """
    return 25.4 / _cpi(pdf)


def _row_unit(pdf):
    """Altura da LINHA em mm: `25,4 / LPI`. Substitui a constante `_row_unit(pdf)`."""
    return 25.4 / _lpi(pdf)


def _size(pdf):
    """Corpo da fonte em pt, DERIVADO do LPI: `60 / LPI` (6 -> 10pt, 8 -> 7.5pt).

    Não é escolha: é o que faz o glifo caber na linha em qualquer LPI, com a
    mesma folga (a tinta máxima da fonte ≤ 1,2em é o limite). Por isso
    `font_size` saiu — declarar um corpo solto quebraria a relação.
    """
    return 60.0 / _lpi(pdf)


def _validate_flags(value, label, where='item'):
    """`''` | `'N'` | `'E'` | `'C'` | `'EC'` — a matriz de impressora.

    `N` é o "sem modificador" explícito e por isso não combina com E/C: `'NE'`
    seria pedir normal e expandido juntos, e deixar passar seria uma letra
    ignorada em silêncio. A ordem também não importa.
    """
    from ajsystem.defs.fonts import flags as _flags
    try:
        return _flags(value)
    except ValueError as exc:
        raise ValueError(
            f"report '{label}': flags do {where} — {exc}") from None


def _font_info(pdf, nome=None):
    """Métricas da família. `nome` wins; sem ele, a que está no `pdf`."""
    from ajsystem.defs.fonts import font
    return font(nome if nome is not None else getattr(pdf, '_fonte', 'courier'))


def _apply_face(pdf, style='', cpi=None, cfg=None):
    """Família + estilo + corpo + alongamento, juntos e NESSA ordem.

    Ponto único de aplicação por três motivos, todos medidos:

    1. `get_string_width` já conta o alongamento, então `align='C'`/`'R'` e a
       justificação saem certos — **desde que o alongamento venha ANTES da
       medição**, e medir antes de esticar daria a largura do glifo cru.
    2. O `Tz` é pegadioso: o fpdf2 só o emite na MUDANÇA e o repete no primeiro
       texto de cada página, e o reset de `_beginpage` não segura. Um desenho que
       esquecesse de esticar herdaria o do desenho anterior, em silêncio, e o
       erro atravessaria a quebra de página.
    3. `set_font` não registra a face: sem `add_font` prévio, `set_font(x, 'I')`
       levanta `Undefined font` do fpdf2 no meio do relatório.

    `cfg` é o cfg do item: as props `cpi`/`flags` dele valem só para este
    desenho e não mexem no estado do fluxo — senão um título expandido empurraria
    a coluna do resto do report. `cpi` pronto sobrescreve tudo (usado pela
    cascata de título, que já resolveu o valor).
    """
    from ajsystem.defs.fonts import register, stretch_pct
    info = _font_info(pdf)
    register(pdf, info['name'])
    body = _size(pdf)
    pdf.set_font(info['core'] or info['family'], style or '', body)
    pdf.set_stretching(stretch_pct(info['advance'], body,
                                   _cpi_de(pdf, cfg) if cpi is None else cpi))
    return info


def _validate_style(style, label, where='item'):
    """Centralizada: `''|B|I|U|BI|BU|IU|BIU` — as 8 do fpdf2.

    Antes o `TITLE` e a tabela validavam e `FIELD`/`TEXT` não, então um estilo
    inválido escapava e explodia dentro do fpdf2, com mensagem de outra
    biblioteca. E `U` estava prometido na docstring de `defs/fonts.py` e
    recusado pelo código.
    """
    from ajsystem.defs.fonts import STYLES
    if style not in STYLES:
        _ok = '|'.join(s if s else "''" for s in STYLES)
        raise ValueError(
            f"report '{label}': style do {where} deve ser {_ok}, veio {style!r}")
    return style



def _grid_pos(pdf):
    """Cursor corrente em grade (PCOL, PROW)."""
    col_w = _col_unit(pdf)
    return ((pdf.get_x() - pdf.l_margin) / col_w,
            (pdf.get_y() - pdf.t_margin) / _row_unit(pdf), col_w)


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


def _zone_cols(pdf):
    """(l, r) da zona em COLS: interseção de `IND` com a faixa do logo.

    O `LOGO('L')`/`('R')` não desenha e volta a ignoring: ele **encolhe a zona**
    pelo espaço vago ao lado da imagem, para o texto que divide a faixa com ele.
    A faixa é calculada do CURSOR a cada chamada, então sair dela devolve a área
    útil sozinho — sem comando para desfazer. `IND()` (nu) cancela as duas
    contribuições, porque é o "restaura a área" que já significa.

    Colunas das duas contribuições são absolutas da margem esquerda (o `IND` é
    declarado assim, e o logo sai de `resolve_anchor`, que usa `area_cols`), e
    por isso a interseção é um `max`/`min` e não uma soma — somar daria a zona
    duas vezes no ponto onde as duas se encontram.
    """
    ind = getattr(pdf, '_ind', None)
    l = ind[0] if ind else 0.0
    r = ind[1] if ind else _usable_cols(pdf)
    logo = getattr(pdf, '_logo_zone', None)
    if logo is not None and not (logo['y1'] - 0.01 <= pdf.get_y() <= logo['y2'] + 0.01):
        logo = None      # cursor saiu da faixa do logo
    if logo:
        if logo['l'] is not None:
            l = max(l, logo['l'])
        if logo['r'] is not None:
            r = min(r, logo['r'])
    return l, r


def _flow_zone(pdf):
    """(x0_mm, right_mm) do fluxo: zona (IND ∩ faixa do logo) ou área útil."""
    col_w = _col_unit(pdf)
    l, r = _zone_cols(pdf)
    return pdf.l_margin + l * col_w, pdf.l_margin + r * col_w


def _zone_ncols(pdf):
    """Cols da zona — é contra isto que `location`/`pos`/`TABS` são validados."""
    l, r = _zone_cols(pdf)
    return r - l


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
    """Âncora [col, lin] de location/pos (grade, origem na ZONA).

    Origem na zona e não na margem: com o logo encolhendo a zona, uma posição
    que ignora isso cairia dentro da imagem. `c2` é a última coluna da zona.
    """
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
    if c > _zone_ncols(pdf) + 0.01:
        raise ValueError(
            f"report '{label}': âncora {list(loc)[:2]} na coluna {c:g}, "
            f"fora da zona ({_zone_ncols(pdf):.1f} cols)")
    pdf.set_xy(_flow_zone(pdf)[0] + c * col_w, pdf.t_margin + r * _row_unit(pdf))


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
    """X da parada tab:N (1-based), em cols a partir da ZONA. Y segue o fluxo.

    Relativa à zona, e não à margem: com o logo encolhendo a zona, uma parada
    absoluta cairia dentro da imagem — e, antes disso, uma parada dentro de um
    `IND` maior que a zona desenhava FORA dele.
    """
    tabs = getattr(pdf, '_tabs', None) or []
    if not isinstance(tab, int) or isinstance(tab, bool) or not 1 <= tab <= len(tabs):
        raise ValueError(f"report '{label}': tab:{tab} inválido (TABS tem {len(tabs)} paradas)")
    col_w = _col_unit(pdf)
    if tabs[tab - 1] > _zone_ncols(pdf) + 0.01:
        raise ValueError(
            f"report '{label}': parada {tabs[tab - 1]:g} cols fora da zona "
            f"({_zone_ncols(pdf):.1f} cols)")
    pdf.set_x(_flow_zone(pdf)[0] + tabs[tab - 1] * col_w)


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
    # Sem `IND`: a zona ainda pode estar encolhida pelo logo — usa ela, e só
    # quando não houver uma última tabela mais estreita.
    esq, dir_ = _table_edges(pdf)
    if getattr(pdf, '_logo_zone', None) and pdf._table_bounds is None:
        zl, zr = _zone_cols(pdf)
        return [zl, r, zr - zl, 0]
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
            pdf.ln(_row_unit(pdf))
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
    if 'font' in cfg:
        raise ValueError(
            f"report '{label}': a prop 'font' é do report (uma família para o "
            f"documento inteiro); no item use 'cpi'")
    _fl_item = cfg.get('flags')
    if _fl_item is not None:
        _validate_flags(_fl_item, label, kind)
    col_w = _col_unit(pdf, cfg)
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
        _apply_face(pdf, 'B', cfg=cfg)
        # `+ 2` aqui NÃO é respiro desenhado: o fpdf posiciona a próxima célula
        # em `new_x="END"`, que é a borda do TEXTO (o respiro real é o
        # `c_margin` do fpdf). Este `2` é largura de CAIXA, e só entra na conta
        # de estouro logo abaixo. Por isso não vira `GAP_LABEL`: o respiro em
        # cols vive no `MEMO`, onde o prefixo é desenhado com a largura que a
        # quebra usou.
        lw = (pdf.get_string_width(lbl + ': ') + 2) if lbl else 0
        _apply_face(pdf, '', cfg=cfg)
        vw = pdf.get_string_width(txt or '') + 2
        if _want_wrap(cfg, kind, label):
            # Rótulo na primeira linha (como `cell`), valor quebrando no resto da
            # zona. `FIELD` sempre aperta o valor na largura do texto; aqui ele
            # passa a ocupar a linha, que é o que uma frase precisa.
            if lbl:
                _apply_face(pdf, 'B', cfg=cfg)
                pdf.cell(lw, _row_unit(pdf), lbl + ': ', new_x="END")
                _apply_face(pdf, '', cfg=cfg)
            pdf.multi_cell(_wrap_width(pdf, cfg.get('width')), _row_unit(pdf), txt,
                           new_x="LMARGIN", new_y="NEXT")
            if txt:
                _mark_content(pdf)
            return
        if not _fixed and pdf.get_x() + lw + vw > right + 0.01 and pdf.get_x() > _x0 + 0.01:
            pdf.ln(_row_unit(pdf))  # pcol+1>ncol -> pcol=1, prow+=1
            pdf.set_x(_x0)
        if lw + vw > right - _x0:
            txt, vw = _cut_to_fit(pdf, txt, right - _x0 - lw), right - _x0 - lw
        if lbl:
            _apply_face(pdf, 'B', cfg=cfg)
            pdf.cell(lw, _row_unit(pdf), lbl + ': ', new_x="END")
            _apply_face(pdf, '', cfg=cfg)
        pdf.cell(vw, _row_unit(pdf), txt, new_x="END", new_y="TOP")
        if txt:
            _mark_content(pdf)
    else:  # TEXT
        from ajsystem.core.text import dotted_get as _dg
        txt = _trender(cfg.get('text', ''), lambda k: _dg(instance, k) if instance is not None else None, cfg.get('_fmt_opts'))
        _validate_style(cfg.get('style', '') or '', label, 'TEXT')
        _apply_face(pdf, cfg.get('style', '') or '', cfg=cfg)
        if _want_wrap(cfg, kind, label):
            # `wrap`: quebra na zona em vez de cortar a ponta. `multi_cell`
            # ocupa a linha toda, então `align` R/C passa a valer no texto
            # quebrado também — e `_cut_to_fit` some de propósito, que era ele
            # que comia o resto da frase.
            if not _fixed and pdf.get_x() > _x0 + 0.01 and cfg.get('width') is None:
                pdf.set_x(_x0)
            pdf.multi_cell(_wrap_width(pdf, cfg.get('width')), _row_unit(pdf), txt,
                           align=cfg.get('align', 'L'),
                           new_x="LMARGIN" if not _fixed else "END", new_y="NEXT")
            if txt:
                _mark_content(pdf)
            return
        _w = cfg.get('width')
        if _w is not None:
            if isinstance(_w, bool) or not isinstance(_w, (int, float)) or _w <= 0:
                raise ValueError(f"report '{label}': width deve ser cols > 0")
            _w = _w * _col_unit(pdf, cfg)
            _apply_face(pdf, cfg.get('style', '') or '', cfg=cfg)
        elif fill and not _fixed:
            _w = right - pdf.get_x()
            if pdf.get_string_width(txt or '') + 2 > _w:
                txt = _cut_to_fit(pdf, txt, _w)  # linha própria: trunca na zona
        else:
            _w = pdf.get_string_width(txt or '') + 2
        if not _fixed and pdf.get_x() + _w > right + 0.01 and pdf.get_x() > _x0 + 0.01:
            pdf.ln(_row_unit(pdf))
            pdf.set_x(_x0)
        if _w > right - _x0:
            txt, _w = _cut_to_fit(pdf, txt, right - _x0), right - _x0
        pdf.cell(_w, _row_unit(pdf), txt, align=cfg.get('align', 'L'), new_x="END", new_y="TOP")
        if txt:
            _mark_content(pdf)


def _respiro(pdf, cfg, prop, label=''):
    """`rows_before`/`rows_after`: n LINHAS de respiro, e o cursor volta para a
    1ª coluna da zona.

    Função única, chamada nos dois lados do item. Antes o bloco ficava no FIM do
    laço de `_render_items`, e todo item que dava `continue` (MEMO, TITLE, LF...)
    simplesmente nunca chegava nele — `rows_before` no `MEMO` era lido e
    ignorado calado, e o autor tinha de escrever um `LF(1, {'when': ...})` na mão
    para respirar antes do bloco. Agora a regra é uma só, e vale para todo item.
    """
    n = cfg.get(prop, 0) or 0
    if isinstance(n, bool) or not isinstance(n, (int, float)) or n < 0:
        raise ValueError(f"report '{label}': {prop} deve ser número >= 0")
    if n:
        pdf.ln(n * _row_unit(pdf))
        pdf.set_x(_flow_zone(pdf)[0])


def _render_items(pdf, items, instance, report, reset_tabs=True):
    """Itens inline em ordem, antes da tabela. rows_before/after em linhas.

    TABS ([n...], diretiva) ancora X por tab:N (Y no fluxo); POS ([c,r])
    salta o cursor; PROW/PCOL valem em âncora. reset_tabs=False preserva as
    paradas vigentes (uso interno do header, que renderiza item a item).
    """
    from ajsystem.core.geom import normalize as _gloc, to_mm as _gmm
    from ajsystem.core.text import render as _trender
    label = report.label if report is not None else ''
    from ajsystem.defs.fonts import CPI_DEFAULT, LPI_DEFAULT, cpi as _cpi_norm, lpi as _lpi_norm
    if reset_tabs:
        pdf._tabs = None
        pdf._cpi = CPI_DEFAULT
        pdf._flags = ''
        pdf._lpi = LPI_DEFAULT
        pdf._ind = None
        pdf._logo_zone = None
    col_w = _col_unit(pdf)
    _titulos = 0   # cascata de TITLE desta lista (1º = título, demais = subtítulo)

    def _um_item(kind, name, cfg, col_w, drawn):
        """Desenha 1 item. Devolve `(col_w, drawn)`: o `CPI`/`LPI` muda a
        grade do fluxo e o `TITLE`/`TITLES` o contador da cascata — os dois
        atravessam o item, então voltam em vez de sumir.
        """
        if kind in ('CPI', 'LPI'):
            # Diretiva de GRADE: muda a célula/coluna do fluxo daqui em diante.
            # `CPI()`/`LPI()` nu volta ao padrão — é o "restaura" do antigo FONT.
            if kind == 'CPI':
                pdf._cpi = _cpi_norm(cfg['cpi']) if 'cpi' in cfg else CPI_DEFAULT
                pdf._flags = cfg.get('flags', '')
            else:
                pdf._lpi = _lpi_norm(cfg['lpi']) if 'lpi' in cfg else LPI_DEFAULT
            return _col_unit(pdf), drawn
        if kind in ('PCOL', 'PROW'):
            # Diretiva de cursor: `PCOL(n)` = n cols do INÍCIO DA ZONA (que o
            # logo pode ter encolhido), `PROW(n)` = linha n da margem de topo.
            _n = cfg.get('offset', 0)
            if kind == 'PCOL':
                if _n > _zone_ncols(pdf) + 0.01:
                    raise ValueError(
                        f"report '{label}': PCOL({_n:g}) fora da zona "
                        f"({_zone_ncols(pdf):.1f} cols)")
                pdf.set_x(_flow_zone(pdf)[0] + _n * col_w)
            else:
                pdf.set_y(pdf.t_margin + _n * _row_unit(pdf))
            return col_w, drawn
        if kind == 'TABS':
            _stops = [_eval_tab_value(pdf, _s, label) for _s in (cfg.get('values') or [])]
            if sorted(_stops) != list(_stops):
                raise ValueError(f"report '{label}': TABS deve vir em ordem crescente")
            pdf._tabs = list(_stops)
            return col_w, drawn
        if kind == 'CALL':
            try:
                _txt = cfg['fn'](instance) if instance is not None else ''
            except Exception:
                _txt = ''
            if _txt:
                _apply_face(pdf)
                pdf.cell(0, _row_unit(pdf), _txt, new_x="LMARGIN", new_y="NEXT")
                _mark_content(pdf)
            return col_w, drawn
        if kind == 'POS':
            _c, _r = _resolve_tokens(pdf, cfg.get('values'), label)
            for _v in (_c, _r):
                if isinstance(_v, bool) or not isinstance(_v, (int, float)):
                    raise ValueError(f"report '{label}': POS exige [col, lin]")
            pdf.set_xy(pdf.l_margin + _c * col_w, pdf.t_margin + _r * _row_unit(pdf))
            return col_w, drawn
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
            return col_w, drawn
        if kind in ('TITLE', 'TITLES'):
            # Título no corpo é o MESMO desenho do header (mesmo helper, mesma
            # cascata por posição). A cascata é desta lista de items — cada
            # `before`/`after` recomeça, como no header.
            # `tab` não existe aqui (as paradas são do header), então é recusado
            # nomeando a prop em vez de ancorar no lugar errado sem avisar.
            if 'tab' in cfg:
                raise ValueError(
                    f"report '{label}': TITLE no corpo não aceita 'tab' — "
                    f"use 'location'/'pos'")
            if kind == 'TITLE':
                drawn = _draw_titulo(pdf, cfg, None, label, instance=instance, drawn=drawn)
            else:
                for _sub in cfg.get('items') or []:
                    _k, _n, _cfg = _split_item(_sub, label)
                    if _k != 'TITLE':
                        raise ValueError(f"report '{label}': TITLES aceita só TITLE, veio {_k!r}")
                    if 'tab' in _cfg:
                        raise ValueError(
                            f"report '{label}': TITLE no corpo não aceita 'tab' — "
                            f"use 'location'/'pos'")
                    drawn = _draw_titulo(pdf, _cfg, None, label, instance=instance, drawn=drawn)
            return col_w, drawn
        if kind == 'MEMO':
            _validate_flags(cfg.get('flags'), label, 'MEMO')
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
            _style = cfg.get('style', '') or ''
            _validate_style(_style, label, 'MEMO')
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
            # Rótulo = PREFIXO da 1ª linha (era uma linha própria, e o `MEMO`
            # era o único item que empurrava o texto para baixo — o `FIELD` já
            # era inline). A 1ª linha quebra na medida que sobra DEPOIS do
            # rótulo, então o mesmo número (`_lw`) vai para o `first` do wrap e
            # para o desenho: recalcular em cada lado é a chance de a linha caber
            # na conta e não no papel.
            _lw = 0.0
            if _lbl:
                _apply_face(pdf, 'B', cfg=cfg)
                _lw = (pdf.get_string_width(_lbl)
                       + GAP_LABEL * _col_unit(pdf, cfg))
            if _txt and _lw and _w - _recuo - _lw <= 0:
                raise ValueError(
                    f"report '{label}': MEMO sem medida na 1ª linha — "
                    f"recuo {_recuo:.1f}mm + rótulo {_lw:.1f}mm >= width {_w:.1f}mm")
            if _lbl and not _txt:
                # sem texto não há linha para apoiar: o rótulo fica sozinho, como
                # antes — a linha dele é a largura do rótulo mais o respiro.
                _apply_face(pdf, 'B', cfg=cfg)
                pdf.set_x(_bx)
                pdf.cell(_lw, _row_unit(pdf), _lbl, new_x="END", new_y="NEXT")
            # A fonte ANTES de medir: `_wrap_linhas` decide onde quebrar pelo
            # `get_string_width`, e medir na fonte anterior produz linhas mais
            # largas que o bloco (o bloco saía com 154mm num espaço de 141mm).
            _apply_face(pdf, _style, cfg=cfg)
            _linhas = _wrap_linhas(pdf, _txt, _w, first=_w - _recuo - _lw) if _txt else []
            if _linhas:
                _draw_bloco(pdf, _linhas, _bx, _w, _row_unit(pdf), _style,
                            cfg.get('align', MEMO_ALIGN), _recuo,
                            prefixo=(_lbl, 'B', _lw))
                pdf.set_x(_flow_zone(pdf)[0])
            return col_w, drawn
        if kind == 'CR':
            pdf.set_x(_flow_zone(pdf)[0])  # volta à 1ª coluna, mesma linha
            return col_w, drawn
        if kind == 'LF':
            _n = cfg.get('lines', 1)
            if isinstance(_n, bool) or not isinstance(_n, (int, float)) or _n < 1:
                raise ValueError(f"report '{label}': LF exige lines >= 1")
            pdf.ln(_n * _row_unit(pdf))
            pdf.set_x(_flow_zone(pdf)[0])
            return col_w, drawn
        if kind == 'FF':
            if getattr(pdf, '_in_header', False):
                raise ValueError(f"report '{label}': FF só no corpo (header repete por página)")
            pdf.add_page()
            return col_w, drawn
        if kind == 'IND':
            _vals = cfg.get('values') or []
            if not _vals:
                # `IND()` nu = restaura a área útil: cancela o `IND` E o recuo
                # do logo, para dar para voltar ao que era mesmo estando dentro
                # da faixa dele.
                pdf._ind = None
                pdf._logo_zone = None
                return col_w, drawn
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
            return col_w, drawn
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
                     _row_unit(pdf), col_w)
            ox, oy = pdf.l_margin, pdf.t_margin
            if kind == 'LINE':
                if g.get('ponto'):
                    # Extensão (0,0): um `line` degenerado emitiria um
                    # subcaminho de comprimento zero e não pintaria nada —
                    # o ponto vira disco. Raio = 1/8 da coluna, para acompanhar
                    # o pitch da fonte vigente (col_w = 25.4/CPI).
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
                pdf.ln(_row_unit(pdf))
                pdf.set_x(_flow_zone(pdf)[0])
        return col_w, drawn
    for it in items or []:
        kind, name, cfg = _split_item(it, label)
        if kind == 'FIELDS':
            raise ValueError(f"report '{label}': FIELDS deve ser expandido no apply (do_report)")
        if kind in ('FIELD', 'TEXT', 'LINE', 'BOX', 'CIRCLE', 'MEMO', 'LF', 'TITLE') \
                and cfg.get('when') is not None:
            from ajsystem.core.text import eval_when as _ew
            if not _ew(instance, cfg['when']):
                continue
        _respiro(pdf, cfg, 'rows_before', label)
        col_w, _titulos = _um_item(kind, name, cfg, col_w, _titulos)
        if kind not in ('TITLE', 'TITLES'):
            # o título já aplicou o próprio `rows_after` (padrão 1 linha)
            _respiro(pdf, cfg, 'rows_after', label)


def _margin_mm(v, label):
    """Margem em mm ou {'cols': n} (cols draft 2.54mm). Congelada aqui: troca
    de fonte nunca recalcula margem."""
    from ajsystem.defs.fonts import col_mm, CPI_DEFAULT
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

    # Família do documento inteiro. Validada aqui (não no 1º desenho) para que
    # nome errado caia antes de qualquer página sair — e o registro das faces
    # acontece agora, porque `_beginpage` reseta a fonte e quem tem que
    # reaplicar depois da quebra é `_apply_face`, sempre.
    pdf._fonte = _font_info(pdf, report.font)['name']
    from ajsystem.defs.fonts import register
    register(pdf, pdf._fonte)

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
            pdf.ln(int(_bl['rows_before']) * _row_unit(pdf))

    # Tabela
    tbl = _build_table(report)
    if tbl.columns:
        _render_table(pdf, tbl.columns, data, tbl.totals,
                      instance, report=report)
    if tbl.rows_after:
        pdf.ln(tbl.rows_after * _row_unit(pdf))

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
                _apply_face(pdf)
                pdf.cell(0, _row_unit(pdf), txt, new_x="LMARGIN", new_y="NEXT")

    # Texts avulsos
    if report.texts:
        for txt in report.texts:
            if txt.when == 'end_of_report':
                pdf.ln(GAP_TEXTS)
                _apply_face(pdf, txt.style)
                pdf.cell(0, _row_unit(pdf), txt.text, align=txt.align,
                         new_x="LMARGIN", new_y="NEXT")

    return pdf
