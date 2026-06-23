from app.extensions import db


class Transacao(db.Model):
    __tablename__ = "transacao"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(1), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    rubrica_id = db.Column(db.Integer, db.ForeignKey("rubrica.id"), nullable=True)
    fatura = db.Column(db.String(50), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    historico = db.Column(db.Text, nullable=True)
    cancelado = db.Column(db.Date, nullable=True)

    conta = db.relationship("Conta", backref="transacoes")
    rubrica = db.relationship("Rubrica", backref="transacoes")
    previsoes = db.relationship("Previsao", backref="transacao", cascade="all, delete-orphan",
                                order_by="Previsao.vencimento, Previsao.id")

    @property
    def status(self):
        if self.cancelado:
            return 8
        if not self.previsoes or sum(float(p.previsto) for p in self.previsoes) < float(self.valor):
            return 0
        return max(p.status for p in self.previsoes)

    @property
    def status_label(self):
        from app.constants import PREVISAO_STATUS
        return PREVISAO_STATUS.get(self.status, "")
