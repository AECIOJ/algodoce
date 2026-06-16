from io import BytesIO
from fpdf import FPDF


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
