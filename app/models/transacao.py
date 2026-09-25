from ajsystem.core.extensions import db
from ajsystem.defs.constants import POS_0_NOT_EMPTY
from app.constantes import TIPO_TRANSACAO, STATUS_PREVISAO


class Transacao(db.Model):
    __tablename__ = "transacao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(1), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    operacao_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    fatura = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    variacao = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    saldo = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    prazo = db.Column(db.String(100), nullable=False, default='')
    historico = db.Column(db.Text, nullable=True)
    cancelado = db.Column(db.Date, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True, unique=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id"), nullable=True, unique=True)

    conta = db.relationship("Conta", backref="transacoes")
    operacao = db.relationship("Operacao", backref="transacoes")
    pedido = db.relationship("Pedido", uselist=False,
                             backref=db.backref("transacao", uselist=False))
    compra = db.relationship("Compra", uselist=False,
                             backref=db.backref("transacao", uselist=False))
    previsoes = db.relationship("Previsao", backref="transacao",
                                order_by="Previsao.vencimento, Previsao.id")

    def calc_prazo(self):
        """Resumo dos vencimentos em dias a partir de `data` (ex.: '30/60/90')."""
        if not self.previsoes:
            return ''
        return '/'.join(str((p.vencimento - self.data).days) for p in self.previsoes)

    def calc_status(self):
        if self.cancelado:
            return 8
        if not self.previsoes:
            return 0
        restante = float(self.valor or 0) - sum(float(p.previsto or 0)
                                               for p in self.previsoes)
        if restante > 0.005:
            return 0
        return max(p.status for p in self.previsoes)

    @property
    def status_label(self):
        return STATUS_PREVISAO.get(self.calc_status(), "")


Entity = {
    'id':           {'type': 'ID', 'width': 6},
    'data':         {'type': 'DATA', 'width': 12, 'required': True},
    'tipo':         {'type': 'LIST', 'width': 12, 'options': TIPO_TRANSACAO, 'required': True},
    'conta_id':     {'type': 'FK', 'label': 'Conta', 'width': 15, 'required': True,},
    'operacao_id':  {'type': 'FK', 'label': 'Operação', 'width': 15, 'required': True,},
    'fatura':       {'type': 'TEXT', 'width': 12},
    'prazo':        {'type': 'TEXT', 'width': 20, 'readonly': True},
    'valor':        {'type': 'NUM', 'width': 12, 'currency': 1, 'readonly': True},
    'variacao':     {'type': 'NUM', 'width': 10, 'currency': 1, 'readonly': True},
    'saldo':        {'type': 'NUM', 'width': 10, 'currency': 1, 'readonly': True},
    'cancelado':    {'type': 'DATA', 'width': 12},
    'status':       {'type': 'LIST', 'width': 10, 'options': STATUS_PREVISAO},
    'pedido_id':    {'type': 'FK', 'label': 'Pedido', 'width': 9,
                     'pos_form': POS_0_NOT_EMPTY, 'readonly': True,
                     'pos_list': 0, 'tag': {'link': 'pedidos.form', 'color': 'info'}},
    'compra_id':    {'type': 'FK', 'label': 'Compra', 'width': 9,
                     'pos_form': POS_0_NOT_EMPTY, 'readonly': True,
                     'pos_list': 0, 'tag': {'link': 'compras.form', 'color': 'info'}},
    'historico':    {'type': 'MEMO', 'width': 40},
}
