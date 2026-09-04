from datetime import datetime, timezone
from app.ajsystem.core.extensions import db
from app.constantes import ORDER_STATUS, FORMINHAS


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
    carteira_id = db.Column(db.Integer, db.ForeignKey("carteira.id"), nullable=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey("transacao.id"), nullable=True, unique=True)
    movto_id = db.Column(db.Integer, db.ForeignKey("movto.id"), nullable=True, unique=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)

    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=True
    )
    producao = db.relationship("Producao", foreign_keys=[producao_id], lazy="select")
    quote_id = db.Column(
        db.Integer, db.ForeignKey("quotes.id"), nullable=True
    )
    quote = db.relationship("Quote", foreign_keys=[quote_id], lazy="select")
    carteira = db.relationship("Carteira", uselist=False)
    transacao = db.relationship("Transacao", foreign_keys=[transacao_id], uselist=False)
    movto = db.relationship("Movto", foreign_keys=[movto_id], uselist=False)
    event = db.relationship("Event", back_populates="order", uselist=False, lazy="select")
    items = db.relationship(
        "OrderItem", back_populates="order",
        foreign_keys="OrderItem.order_id",
        lazy="select"
    )

    def __repr__(self):
        return f"<Order {self.id} - {self.status}>"


Entity = {
    'id':                    {'type': 'ID', 'width': 6},
    'client_id':             {'type': 'FK', 'label': 'Cliente', 'width': 20, 'required': True},
    'data_pedido':           {'type': 'DATA_HORA', 'label': 'Data Pedido',},
    'data_previsao_entrega': {'type': 'DATA_HORA', 'label': 'Prev. Entrega', },
    'data_entrega':          {'type': 'DATA_HORA', 'label': 'Data Entrega', },
    'carteira_id':           {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'forminhas':             {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
    'total':                 {'type': 'NUM', 'currency': 1, 'readonly': True, 'width': 10},
    'status':                {'type': 'LIST', 'width': 11, 'options': ORDER_STATUS,
                              'tag': {'colors': {0: 'warning', 1: 'info', 2: 'info', 8: 'error', 9: 'success'}}},
    'observacao':            {'type': 'MEMO', 'label': 'Observação', 'pos_list': 0, 'width': 40},
}
