from datetime import datetime, timedelta
from io import BytesIO
from flask_login import current_user
from fpdf import FPDF
from app.constants import FORMINHAS
from app.report import (
    Report, ReportField, ReportColumn, ReportColumns, ReportGroup,
    ReportText, parse_header_field, _ReportHeader, _ReportTable, _ReportFooter,
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


def gerar_pdf_pedido(order, logo_path):
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Logo
    if logo_path:
        pdf.image(logo_path, x=pdf.w / 2 - 30, w=60, h=0)

    # Title
    pdf.ln(35)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Pedido #{order.id}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.w / 4, pdf.get_y(), pdf.w * 3 / 4, pdf.get_y())
    pdf.ln(8)

    # Client info
    pdf.set_font("Helvetica", "", 10)
    client = order.conta
    col_left = 10
    col_right = pdf.w - 10
    mid = pdf.w / 2

    x0 = pdf.get_x()
    y0 = pdf.get_y()

    pdf.set_xy(x0, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(mid - x0, 6, "Cliente:", new_x="END")
    pdf.set_xy(mid, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_right - mid, 6, "Data do Pedido:", align="R", new_x="END")

    y1 = pdf.get_y()
    pdf.set_xy(x0, y0 + 6)
    pdf.set_font("Helvetica", "", 10)
    tel = client.telefone or ""
    pdf.cell(mid - x0, 6, client.nome, new_x="END")
    pdf.set_xy(mid, y0 + 6)
    pdf.set_font("Helvetica", "", 10)
    data_pedido = order.data_pedido.strftime("%d/%m/%Y %H:%M") if order.data_pedido else "-"
    pdf.cell(col_right - mid, 6, data_pedido, align="R", new_x="END")

    pdf.set_xy(x0, y0 + 12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(mid - x0, 6, tel, new_x="END")

    row_h = 18
    if order.data_previsao_entrega:
        pdf.set_xy(mid, y0 + 12)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_right - mid, 6, "Previsão de Entrega:", align="R", new_x="END")
        pdf.set_xy(mid, y0 + 18)
        pdf.set_font("Helvetica", "", 10)
        prev = order.data_previsao_entrega.strftime("%d/%m/%Y %H:%M")
        pdf.cell(col_right - mid, 6, prev, align="R", new_x="END")
        row_h = 24

    if order.data_entrega:
        pdf.set_xy(mid, y0 + row_h)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(col_right - mid, 6, "Entrega:", align="R", new_x="END")
        pdf.set_xy(mid, y0 + row_h + 6)
        pdf.set_font("Helvetica", "", 10)
        entrega = order.data_entrega.strftime("%d/%m/%Y %H:%M")
        pdf.cell(col_right - mid, 6, entrega, align="R", new_x="END")

    pdf.set_y(max(pdf.get_y(), y0 + row_h + 6) + 8)

    # Items table
    col_w = pdf.w - 20
    w_prod = col_w * 0.50
    w_qtd = col_w * 0.10
    w_preco = col_w * 0.20
    w_valor = col_w * 0.20

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(w_prod, 7, "Produto", border=1, align="C", fill=True)
    pdf.cell(w_qtd, 7, "Qtd.", border=1, align="C", fill=True)
    pdf.cell(w_preco, 7, "Preço", border=1, align="C", fill=True)
    pdf.cell(w_valor, 7, "Valor", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for item in order.items:
        nome = item.product.nome
        if item.observacao:
            nome += f" ({item.observacao})"
        preco = item.preco_unitario or 0
        valor = preco * item.quantidade

        pdf.cell(w_prod, 6, nome, border=1)
        pdf.cell(w_qtd, 6, str(item.quantidade), border=1, align="C")
        pdf.cell(w_preco, 6, _fmt(preco), border=1, align="R")
        pdf.cell(w_valor, 6, _fmt(valor), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    # Total
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(w_prod + w_qtd + w_preco, 7, "Total", border=1, align="R")
    pdf.cell(w_valor, 7, _fmt(order.total or 0), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(pdf.w / 2 - 10, 6, f"Forminhas: {FORMINHAS.get(order.forminhas, '-')}")
    pdf.cell(pdf.w / 2 - 10, 6, f"Carteira: {order.carteira.nome or '-'}", align="R", new_x="LMARGIN", new_y="NEXT")

    # Observation
    if order.observacao:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Observação:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, order.observacao)

    return pdf


def gerar_pdf_orcamento(quote, logo_path):
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    if logo_path:
        pdf.image(logo_path, x=pdf.w / 2 - 30, w=60, h=0)

    pdf.ln(35)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Orçamento #{quote.id}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.w / 4, pdf.get_y(), pdf.w * 3 / 4, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    col_left = 10
    col_right = pdf.w - 10
    mid = pdf.w / 2

    x0 = pdf.get_x()
    y0 = pdf.get_y()

    pdf.set_xy(x0, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(mid - x0, 6, "Cliente:", new_x="END")
    pdf.set_xy(mid, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_right - mid, 6, "Data:", align="R", new_x="END")

    pdf.set_xy(x0, y0 + 6)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(mid - x0, 6, quote.cliente_nome, new_x="END")
    pdf.set_xy(mid, y0 + 6)
    pdf.set_font("Helvetica", "", 10)
    data = quote.data_pedido.strftime("%d/%m/%Y %H:%M") if quote.data_pedido else "-"
    pdf.cell(col_right - mid, 6, data, align="R", new_x="END")

    ref = quote.data_renovacao or quote.data_pedido
    venc = (ref + timedelta(days=quote.validade or 3)).strftime("%d/%m/%Y") if ref else "-"
    txt = f"Validade: {venc} ({quote.validade} dias)"
    if quote.data_renovacao:
        txt = f"Renovado: {quote.data_renovacao.strftime('%d/%m/%Y')} | {txt}"
    pdf.set_xy(mid, y0 + 12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(col_right - mid, 6, txt, align="R", new_x="END")

    pdf.set_xy(x0, y0 + 12)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(mid - x0, 6, quote.cliente_telefone or "", new_x="END")

    pdf.set_y(max(pdf.get_y(), y0 + 18) + 8)

    col_w = pdf.w - 20
    w_prod = col_w * 0.50
    w_qtd = col_w * 0.10
    w_preco = col_w * 0.20
    w_valor = col_w * 0.20

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(w_prod, 7, "Produto", border=1, align="C", fill=True)
    pdf.cell(w_qtd, 7, "Qtd.", border=1, align="C", fill=True)
    pdf.cell(w_preco, 7, "Preço", border=1, align="C", fill=True)
    pdf.cell(w_valor, 7, "Valor", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for item in quote.items:
        nome = item.product.nome
        if item.observacao:
            nome += f" ({item.observacao})"
        preco = item.preco_unitario or 0
        valor = preco * item.quantidade

        pdf.cell(w_prod, 6, nome, border=1)
        pdf.cell(w_qtd, 6, str(item.quantidade), border=1, align="C")
        pdf.cell(w_preco, 6, _fmt(preco), border=1, align="R")
        pdf.cell(w_valor, 6, _fmt(valor), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(w_prod + w_qtd + w_preco, 7, "Total", border=1, align="R")
    pdf.cell(w_valor, 7, _fmt(quote.total or 0), border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(pdf.w / 2 - 10, 6, f"Forminhas: {FORMINHAS.get(quote.forminhas, '-')}")
    pdf.cell(pdf.w / 2 - 10, 6, f"Carteira: {quote.carteira.nome or '-'}", align="R", new_x="LMARGIN", new_y="NEXT")

    if quote.event and quote.event.tipo:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 10)
        info = f"Evento: {quote.event.tipo}"
        if quote.event.tema:
            info += f" — {quote.event.tema}"
        pdf.cell(0, 6, info, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        extras = []
        if quote.event.data:
            extras.append(quote.event.data.strftime("%d/%m/%Y"))
        if quote.event.hora:
            extras.append(quote.event.hora.strftime("%H:%M"))
        if quote.event.local:
            extras.append(quote.event.local)
        if extras:
            pdf.cell(0, 5, "  " + " | ".join(extras), new_x="LMARGIN", new_y="NEXT")
        if quote.event.obs:
            pdf.multi_cell(0, 5, f"  {quote.event.obs}")

    if quote.observacao:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Observação:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, quote.observacao)

    return pdf


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
        self._header = report._build_header()
        self._footer_cfg = report._build_footer()
        self._is_first_page = True
        self._instance = None
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
    """Calcula larguras das colunas (percentuais → mm). Retorna (col_widths, total_w, x_start)."""
    avail_w = pdf.w - pdf.l_margin - pdf.r_margin
    total_pct = sum(c.width or 0 for c in cols)
    if total_pct > 0:
        col_widths = [(c.width or 0) / total_pct * avail_w for c in cols]
    else:
        col_widths = [avail_w / len(cols)] * len(cols)
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
        if col.aggregate == 'sum' and val is not None:
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
        if col.aggregate == 'sum':
            last_val = _format_cell_value(agg_values.get(col.field, 0), col.format)
    pdf.set_x(x_start + label_w)
    pdf.cell(col_widths[-1], 7, last_val, border=0, align="R", new_x="LMARGIN", new_y="NEXT")
    _draw_hline(pdf, x_start, total_w)


def _table_close(pdf, x_start, total_w):
    """Linha de fechamento da tabela."""
    _draw_hline(pdf, x_start, total_w)


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

    # Dados
    agg_values = {c.field: 0 for c in cols if c.aggregate}
    header_h = 7 + 6
    gera_cab = True
    num_groups = len(report.groups) if report and report.groups else 0

    for row in data:
        indice = str(row.indice) if row.indice is not None else ''
        depth = len(indice.split('.')) if indice else 0

        if num_groups > 0 and 1 <= depth <= num_groups:
            g = report.groups[depth - 1]
            fmt = g.get('format', {})

            if g.get('position') == 'Titulo':
                if not gera_cab:
                    _table_close(pdf, x_start, total_w)
                    ln_after = (report.table or {}).get('lines_after', 0) if report else 0
                    if ln_after:
                        pdf.ln(ln_after * 6)
                ln_before = (report.table or {}).get('lines_before', 0) if report else 0
                if ln_before:
                    pdf.ln(ln_before * 6)
                if g.get('new_page'):
                    pdf.add_page()
                gera_cab = True

            if g.get('position') == 'Linha':
                page_break = _check_page_break(pdf, 8)
                if gera_cab or page_break:
                    _render_column_headers(pdf, cols, col_widths, x_start, total_w, draw_top_line=True)
                    gera_cab = False

            if report.show_table_lines:
                _draw_hline(pdf, x_start, total_w)
            pdf.set_font("Helvetica", fmt.get('font_style', ''), fmt.get('font_size', 10))
            group_text = f"{indice} {row.nome}"
            indent = fmt.get('indent', 2)
            pdf.set_x(x_start + indent)
            pdf.cell(total_w - indent, 8, group_text, border=0,
                     new_x="LMARGIN", new_y="NEXT")
            if report.show_table_lines:
                _draw_hline(pdf, x_start, total_w)

            continue

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
    # Resolver dados via data_fn se não foram passados explicitamente
    if data is None:
        data = report.data_fn() if report.data_fn else []

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

    # Ordenar dados se ordem especificada
    if report.ordem and data:
        data = sorted(data, key=lambda r: str(_deep_attr(r, report.ordem) or ''))

    # Primeira página
    pdf.add_page()

    # Before table
    _before = report.before_table
    if callable(_before) and instance:
        _before = _before(instance) or []
    if _before:
        _render_table_lines(pdf, _before, instance)

    # Tabela
    tbl = report._build_table()
    if tbl.columns:
        _render_table(pdf, tbl.columns, data, tbl.footer, tbl.footer_label,
                      instance, report=report)
    if tbl.lines_after:
        pdf.ln(tbl.lines_after * 6)

    # After table
    _after = report.after_table
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

