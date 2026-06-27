from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("conta.id"), nullable=False
    )
    data_pedido = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    data_previsao_entrega = db.Column(db.DateTime, nullable=True)
    data_entrega = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)
    observacao = db.Column(db.Text)
    total = db.Column(db.Numeric(10, 2), nullable=True)
    forma_pagamento = db.Column(db.Integer, nullable=False, default=0)
    forma_pagamento_id = db.Column(db.Integer, db.ForeignKey("forma_pagamento.id"), nullable=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey("transacao.id"), nullable=True, unique=True)
    movto_id = db.Column(db.Integer, db.ForeignKey("movto.id"), nullable=True, unique=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)

    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=True
    )
    producao = db.relationship("Producao", foreign_keys=[producao_id], lazy="joined")
    quote_id = db.Column(
        db.Integer, db.ForeignKey("quotes.id"), nullable=True
    )
    quote = db.relationship("Quote", foreign_keys=[quote_id], lazy="joined")
    forma_pagamento_rel = db.relationship("FormaPagamento", uselist=False)
    transacao = db.relationship("Transacao", foreign_keys=[transacao_id], uselist=False)
    movto = db.relationship("Movto", foreign_keys=[movto_id], uselist=False)
    event = db.relationship("Event", back_populates="order", uselist=False, lazy="joined")
    items = db.relationship(
        "OrderItem", back_populates="order",
        foreign_keys="OrderItem.order_id",
        lazy="joined"
    )

    def __repr__(self):
        return f"<Order {self.id} - {self.status}>"
