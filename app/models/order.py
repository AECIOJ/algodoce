from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.Integer, db.ForeignKey("clients.id"), nullable=False
    )
    data_pedido = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    data_entrega = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pendente"
    )
    observacao = db.Column(db.Text)
    total = db.Column(db.Numeric(10, 2))

    items = db.relationship(
        "OrderItem", backref="order", lazy="joined",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.id} - {self.status}>"
