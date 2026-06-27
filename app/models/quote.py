from datetime import datetime, timezone
from app.extensions import db


class Quote(db.Model):
    __tablename__ = "quotes"

    id = db.Column(db.Integer, primary_key=True)
    data_pedido = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    pedido_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text)
    validade = db.Column(db.Integer, nullable=False, default=3)
    forma_pagamento = db.Column(db.Integer, nullable=False, default=0)
    forma_pagamento_id = db.Column(db.Integer, db.ForeignKey("forma_pagamento.id"), nullable=True)
    data_renovacao = db.Column(db.DateTime, nullable=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)

    forma_pagamento_rel = db.relationship("FormaPagamento", uselist=False)
    order = db.relationship("Order", foreign_keys=[pedido_id], lazy="joined")
    event = db.relationship("Event", back_populates="quote", uselist=False, lazy="joined")
    items = db.relationship(
        "QuoteItem", back_populates="quote",
        foreign_keys="QuoteItem.quote_id",
        lazy="joined"
    )

    def __repr__(self):
        return f"<Quote {self.id}>"
