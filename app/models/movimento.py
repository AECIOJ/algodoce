from ajsystem.core.extensions import db


class Movimento(db.Model):
    __tablename__ = "movimentos"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    recurso_id = db.Column(db.Integer, db.ForeignKey("recurso.id"), nullable=False)
    tipo = db.Column(db.String(1), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    previsao_id = db.Column(db.Integer, db.ForeignKey("previsao.id"), nullable=True)
    documento = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    variacao = db.Column(db.Numeric(12, 2), nullable=True, default=0)
    operacao_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    transferencia_id = db.Column(db.Integer, db.ForeignKey("transferencias.id"), nullable=True)
    historico = db.Column(db.Text, nullable=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True, unique=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id"), nullable=True, unique=True)

    recurso = db.relationship("Recurso", backref="movtos")
    conta = db.relationship("Conta", backref="movtos")
    previsao = db.relationship("Previsao", backref="movtos")
    operacao = db.relationship("Operacao", backref="movtos")
    pedido = db.relationship("Pedido", uselist=False,
                             backref=db.backref("movto", uselist=False))
    compra = db.relationship("Compra", uselist=False,
                             backref=db.backref("movto", uselist=False))

    @property
    def historico_display(self):
        if self.historico:
            return self.historico
        if self.variacao is not None and self.variacao != 0:
            return 'Haver na data' if self.variacao < 0 else 'Acréscimos na data'
        return 'Pago na data' if self.tipo == 'S' else 'Recebido na data'

    def __repr__(self):
        return f"<Movimento {self.id} {self.tipo} {self.valor}>"


Entity = {
    'id':           {'type': 'ID', 'width': 7},
    'tipo':         {'type': 'TEXT', 'width': 4, 'required': True},
    'data':         {'type': 'DATA', 'width': 10, 'required': True},
    'recurso_id':   {'type': 'FK', 'label': 'Recurso', 'width': 15, 'required': True},
    'conta_id':     {'type': 'FK', 'label': 'Conta', 'width': 15},
    'previsao_id':  {'type': 'FK', 'label': 'Previsão', 'width': 10},
    'documento':    {'type': 'TEXT', 'width': 10},
    'valor':        {'type': 'NUM', 'width': 10, 'currency': 1, 'required': True},
    'operacao_id':  {'type': 'FK', 'label': 'Operação', 'width': 15},
    'variacao':     {'type': 'NUM', 'label': 'Variação', 'width': 10},
    'historico':    {'type': 'MEMO', 'label': 'Histórico', 'width': 30},
    'pedido_id':    {'type': 'FK', 'label': 'Pedido', 'width': 9, 'readonly': True},
    'compra_id':    {'type': 'FK', 'label': 'Compra', 'width': 9, 'readonly': True},
}
