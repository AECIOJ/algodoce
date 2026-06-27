import os
import markdown
from app.constants import CONECTORES, TRANSFORMAR_AO_SALVAR


def render_pagina(nome):
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dados", "paginas", f"{nome}.md",
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return markdown.markdown(content, extensions=["extra"])
    except FileNotFoundError:
        return None


def parse_brl(value):
    if not value:
        return None
    if ',' in value:
        return float(value.replace('.', '').replace(',', '.'))
    return float(value)


def fmt_id(value):
    if value is None:
        return '0'
    formatted = f'{value:,}'.replace(',', '.')
    return ('%7s' % formatted).replace(' ', '\u00A0')


def fmt_brl(value):
    if value is None:
        return '0,00'
    return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def preco_unit(valor, qtd):
    if not valor:
        return 0
    if not qtd:
        return float(valor)
    return float(valor) / float(qtd)


def fmt_zero(value):
    if not value:
        return ''
    return "%.1f" % value


def fmt_date(value):
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def fmt_zero_int(value):
    if not value:
        return ''
    return "%.0f" % value


class LinhaTransacao:
    """Wrapper que permite listar transações com ou sem previsões."""
    __slots__ = ("transacao", "previsao")
    def __init__(self, transacao, previsao=None):
        self.transacao = transacao
        self.previsao = previsao
    @property
    def status(self):
        if self.previsao:
            return self.previsao.status
        return self.transacao.status
    @property
    def vencimento(self):
        return self.previsao.vencimento if self.previsao else self.transacao.data
    @property
    def previsto(self):
        return self.previsao.previsto if self.previsao else None
    @property
    def realizado(self):
        return self.previsao.realizado if self.previsao else None
    @property
    def variacao(self):
        return self.previsao.variacao if self.previsao else None
    @property
    def saldo(self):
        if self.previsao:
            return self.previsao.saldo
        return float(self.transacao.valor)
    @property
    def documento(self):
        return self.previsao.documento if self.previsao else None
    @property
    def id(self):
        return self.previsao.id if self.previsao else None


def _title_case(text):
    words = text.strip().split()
    result = []
    for i, w in enumerate(words):
        if i > 0 and w.lower() in CONECTORES:
            result.append(w.lower())
        else:
            result.append(w[0].upper() + w[1:].lower() if w else w)
    return " ".join(result)


def aplicar_transformacao(mapper, connection, target):
    instance = target
    cls_name = instance.__class__.__name__
    regras = TRANSFORMAR_AO_SALVAR.get(cls_name, {})
    if not regras:
        return
    for campo, modo in regras.items():
        valor = getattr(instance, campo, None)
        if not valor or not isinstance(valor, str) or not valor.strip():
            continue
        if modo == 0:
            setattr(instance, campo, valor.strip().lower())
        elif modo == 1:
            setattr(instance, campo, _title_case(valor.strip()))
        elif modo == 2:
            setattr(instance, campo, valor.strip().upper())
