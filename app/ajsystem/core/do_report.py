"""Orquestrador `do_report` — request → response para relatórios PDF.

O motor fica em `core/pdf.py` (gerar_pdf_relatorio); este módulo concentra o
glue request→response: gera o PDF, serializa em buffer e devolve um
`Response` com `mimetype=application/pdf` e `Content-Disposition` de
visualização inline (ou o PDF pronto, quando `as_response=False`).
"""
from io import BytesIO

from flask import Response

from app.ajsystem.core.pdf import gerar_pdf_relatorio


def do_report(report, data=None, logo_path=None, instance=None,
              filename="relatorio.pdf", as_response=True):
    """Gera e devolve o relatório configurado por `report`.

    `as_response=True` → `flask.Response` (inline PDF) para a rota retornar.
    `as_response=False` → objeto FPDF (para testes/uso programático).
    """
    pdf = gerar_pdf_relatorio(report, data, logo_path, instance=instance)
    if not as_response:
        return pdf
    buf = BytesIO()
    pdf.output(buf)
    return Response(
        buf.getvalue(),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )
