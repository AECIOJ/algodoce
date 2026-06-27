from app.extensions import db


class Previsao(db.Model):
    __tablename__ = "previsao"

    id = db.Column(db.Integer, primary_key=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey("transacao.id"), nullable=False)
    documento = db.Column(db.String(50), nullable=True)
    vencimento = db.Column(db.Date, nullable=False)
    previsto = db.Column(db.Numeric(12, 2), nullable=False)
    realizado = db.Column(db.Numeric(12, 2), nullable=True)
    variacao = db.Column(db.Numeric(12, 2), nullable=True, server_default="0")
    forma_pagamento_id = db.Column(db.Integer, db.ForeignKey("forma_pagamento.id"), nullable=True)
    taxa = db.Column(db.Numeric(5, 2), nullable=False, default=0)

    forma_pagamento = db.relationship("FormaPagamento", uselist=False)

    @property
    def status(self):
        if self.transacao and self.transacao.cancelado:
            return 8
        if self.transacao and sum(float(p.previsto) for p in self.transacao.previsoes) < float(self.transacao.valor):
            return 0
        if self.realizado is None:
            return 1
        base = float(self.previsto) + float(self.variacao or 0)
        return 9 if float(self.realizado) >= base else 2

    @property
    def saldo(self):
        return float(self.previsto) + float(self.variacao or 0) - float(self.realizado or 0)
