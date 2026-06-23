from app.extensions import db


class Movto(db.Model):
    __tablename__ = "movto"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    recurso_id = db.Column(db.Integer, db.ForeignKey("recurso.id"), nullable=False)
    tipo = db.Column(db.String(1), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    previsao_id = db.Column(db.Integer, db.ForeignKey("previsao.id"), nullable=True)
    documento = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    variacao = db.Column(db.Numeric(12, 2), nullable=True, default=0)
    sincronizar = db.Column(db.Boolean, nullable=False, default=True)
    rubrica_id = db.Column(db.Integer, db.ForeignKey("rubrica.id"), nullable=True)
    historico = db.Column(db.Text, nullable=True)

    recurso = db.relationship("Recurso", backref="movtos")
    conta = db.relationship("Conta", backref="movtos")
    previsao = db.relationship("Previsao", backref="movtos")
    rubrica = db.relationship("Rubrica", backref="movtos")

    @property
    def historico_display(self):
        if self.historico:
            return self.historico
        if self.variacao is not None and self.variacao != 0:
            return 'Haver na data' if self.variacao < 0 else 'Acréscimos na data'
        return 'Pago na data' if self.tipo == 'S' else 'Recebido na data'

    def __repr__(self):
        return f"<Movto {self.id} {self.tipo} {self.valor}>"
