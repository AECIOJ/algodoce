from ajsystem.core.extensions import db
from app.constantes import TIPO_TRANSACAO


class Transacao(db.Model):
    __tablename__ = "transacao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(1), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    operacao_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    fatura = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    historico = db.Column(db.Text, nullable=True)
    cancelado = db.Column(db.Date, nullable=True)
    total_previsto = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    conta = db.relationship("Conta", backref="transacoes")
    operacao = db.relationship("Operacao", backref="transacoes")
    previsoes = db.relationship("Previsao", backref="transacao",
                                order_by="Previsao.vencimento, Previsao.id")

    @property
    def status(self):
        if self.cancelado:
            return 8
        if not self.previsoes or abs(float(self.total_previsto or 0) - float(self.valor)) > 0.005:
            return 0
        return max(p.status for p in self.previsoes)

    @property
    def status_label(self):
        from app.constantes import PREVISAO_STATUS
        return PREVISAO_STATUS.get(self.status, "")

    @property
    def compra(self):
        from app.models.compra import Compra
        return Compra.query.filter_by(transacao_id=self.id).first()

    @property
    def pedido(self):
        from app.models.order import Order
        return Order.query.filter_by(transacao_id=self.id).first()


Entity = {
    'id':           {'type': 'ID', 'width': 6},
    'data':         {'type': 'DATA', 'width': 12, 'required': True},
    'tipo':         {'type': 'LIST', 'width': 12, 'options': TIPO_TRANSACAO, 'required': True},
    'conta_id':     {'type': 'FK', 'label': 'Conta', 'width': 15},
    'operacao_id':  {'type': 'FK', 'label': 'Operação', 'width': 15},
    'fatura':       {'type': 'TEXT', 'width': 12},
    'valor':        {'type': 'NUM', 'width': 12, 'currency': 1, 'required': True},
    'historico':    {'type': 'MEMO', 'width': 40, 'pos_list': 2},
    'cancelado':    {'type': 'DATA', 'width': 12, 'pos_list': 0},
    'total_previsto': {'type': 'NUM', 'label': 'Total Previsto', 'width': 12,
                       'currency': 1, 'readonly': True, 'pos_list': 0},
}
