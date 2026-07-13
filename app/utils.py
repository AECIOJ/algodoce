import os
import markdown
from datetime import datetime
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


def deep_attr(obj, path):
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


def fmt_datetime(value):
    if not value:
        return ''
    try:
        return value.strftime('%d/%m/%Y %H:%M')
    except AttributeError:
        return str(value)


class LinhaTransacao:
    """Wrapper que permite listar transações com ou sem previsões."""
    __slots__ = ("transacao", "previsao", "compra")
    def __init__(self, transacao=None, previsao=None, compra=None):
        self.transacao = transacao
        self.previsao = previsao
        self.compra = compra
    @property
    def status(self):
        if self.previsao:
            return self.previsao.status
        if self.transacao:
            return self.transacao.status
        if self.compra:
            return self.compra.status
        return 0
    @property
    def vencimento(self):
        if self.previsao:
            return self.previsao.vencimento
        if self.transacao:
            return self.transacao.data
        return None
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
        if self.transacao:
            return float(self.transacao.valor)
        if self.compra:
            return float(self.compra.valor)
        return 0
    @property
    def documento(self):
        return self.previsao.documento if self.previsao else None
    @property
    def id(self):
        return self.previsao.id if self.previsao else None
    @property
    def fornecedor(self):
        if self.transacao and self.transacao.conta:
            return self.transacao.conta.nome
        if self.compra and self.compra.fornecedor:
            return self.compra.fornecedor.nome
        return None
    @property
    def cliente(self):
        if self.transacao and self.transacao.conta:
            return self.transacao.conta.nome
        return None
    @property
    def conta(self):
        if self.transacao and self.transacao.conta:
            return self.transacao.conta.nome
        if self.compra and self.compra.fornecedor:
            return self.compra.fornecedor.nome
        return None
    @property
    def carteira(self):
        return self.compra.carteira.nome if self.compra and self.compra.carteira else None
    @property
    def fatura(self):
        return self.transacao.fatura if self.transacao else None
    @property
    def valor(self):
        if self.transacao:
            return float(self.transacao.valor)
        if self.compra:
            return float(self.compra.valor)
        return 0
    @property
    def transacao_id(self):
        return self.transacao.id if self.transacao else None
    @property
    def compra_id(self):
        if self.compra:
            return self.compra.id
        if self.transacao:
            c = self.transacao.compra
            return c.id if c else None
        return None
    @property
    def pedido_id(self):
        if self.transacao:
            o = self.transacao.pedido
            return o.id if o else None
        return None
    @property
    def faturado(self):
        return bool(self.transacao) or bool(self.compra and (self.compra.transacao_id or self.compra.movto_id))
    @property
    def status_compra(self):
        if self.compra:
            return self.compra.status
        if self.transacao:
            if hasattr(self.transacao, 'compra') and self.transacao.compra:
                return self.transacao.compra.status
        return None
    @property
    def carteira(self):
        if self.compra and self.compra.carteira:
            return self.compra.carteira.nome
        return None





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


def parse_prazo_recebimento(texto: str, data_pedido, data_entrega, total: float):
    if not texto or not texto.strip():
        return [{"vencimento": data_pedido, "previsto": total}]
    texto = texto.strip().upper()

    # "P/E" — vencimentos no pedido e na entrega
    if texto == "P/E":
        if not data_entrega:
            return [{"vencimento": data_pedido, "previsto": total}]
        split = total / 2
        return [
            {"vencimento": data_pedido, "previsto": round(split, 2)},
            {"vencimento": data_entrega, "previsto": round(total - split, 2)},
        ]

    # "Nx" — N parcelas iguais a cada 30 dias (ex: "3x" → 30/60/90)
    if texto.endswith("X") and texto[:-1].isdigit():
        n = int(texto[:-1])
        if n < 1:
            n = 1
        from datetime import timedelta
        parcelas = []
        for i in range(1, n + 1):
            parcelas.append({
                "vencimento": data_pedido + timedelta(days=30 * i),
                "previsto": round(total / n, 2) if i < n else round(total - (total / n) * (n - 1), 2),
            })
        return parcelas

    # "N" — único vencimento em N dias (ex: "1" → próximo dia)
    if texto.isdigit():
        from datetime import timedelta
        return [{"vencimento": data_pedido + timedelta(days=int(texto)), "previsto": total}]

    # "A/B" — vencimento em A dias e B dias (ex: "0/15")
    if "/" in texto:
        partes = texto.split("/")
        from datetime import timedelta
        dias_lista = [int(p.strip()) for p in partes if p.strip().isdigit()]
        n = len(dias_lista)
        if n == 0:
            return [{"vencimento": data_pedido, "previsto": total}]
        parcelas = []
        for i, dias in enumerate(dias_lista):
            if i == n - 1:
                parcelas.append({
                    "vencimento": data_pedido + timedelta(days=dias),
                    "previsto": round(total - sum(p["previsto"] for p in parcelas), 2),
                })
            else:
                parcelas.append({
                    "vencimento": data_pedido + timedelta(days=dias),
                    "previsto": round(total / n, 2),
                })
        return parcelas

    return [{"vencimento": data_pedido, "previsto": total}]


def _clean(val):
    if not val:
        return None
    s = val.strip()
    if not s or s.lower() == "none":
        return None
    return s


def _save_event(obj, form):
    from app.extensions import db
    from app.models.event import Event
    if not obj.event:
        event = Event()
        obj.event = event
        db.session.add(event)
        db.session.flush()
    event = obj.event
    event.tipo = _clean(form.get("evento_tipo"))
    event.tema = _clean(form.get("evento_tema"))
    event.obs = _clean(form.get("evento_complemento"))
    data_str = form.get("evento_data")
    event.data = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else None
    hora_str = form.get("evento_hora")
    event.hora = datetime.strptime(hora_str, "%H:%M").time() if hora_str else None
    event.local = _clean(form.get("evento_local"))
    conv_str = form.get("evento_convidados")
    event.convidados = int(conv_str) if conv_str else None
    event.cerimonial = _clean(form.get("evento_cerimonial"))
    return event
