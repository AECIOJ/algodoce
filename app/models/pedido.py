from datetime import datetime, timezone
from ajsystem.core.extensions import db
from app.constantes import ORDER_STATUS, FORMINHAS


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(
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
    movimento_id = db.Column(db.Integer, db.ForeignKey("movimentos.id"), nullable=True, unique=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)

    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=True
    )
    producao = db.relationship("Producao", foreign_keys=[producao_id], lazy="select")
    orcamento_id = db.Column(
        db.Integer, db.ForeignKey("orcamentos.id"), nullable=True
    )
    orcamento = db.relationship("Orcamento", foreign_keys=[orcamento_id], lazy="select")
    carteira = db.relationship("Carteira", uselist=False)
    transacao = db.relationship("Transacao", foreign_keys=[transacao_id], uselist=False)
    movto = db.relationship("Movimento", foreign_keys=[movimento_id], uselist=False)
    evento = db.relationship("Evento", back_populates="pedido", uselist=False, lazy="select")
    items = db.relationship(
        "PedidoItem", back_populates="pedido",
        foreign_keys="PedidoItem.pedido_id",
        lazy="select"
    )

    def __repr__(self):
        return f"<Pedido {self.id} - {self.status}>"


Entity = {
    'id':                    {'type': 'ID', 'width': 6},
    'conta_id':             {'type': 'FK', 'label': 'Cliente', 'width': 20, 'required': True},
    'data_pedido':           {'type': 'DATA_HORA', 'label': 'Data Pedido',},
    'data_previsao_entrega': {'type': 'DATA_HORA', 'label': 'Prev. Entrega', 'mask': 'ddd dd/mm/yyyy hh:ii'},
    'data_entrega':          {'type': 'DATA_HORA', 'label': 'Data Entrega', },
    'carteira_id':           {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'forminhas':             {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
    'total':                 {'type': 'NUM', 'currency': 1, 'readonly': True, 'width': 10},
    'status':                {'type': 'LIST', 'width': 11, 'options': ORDER_STATUS,
                              'tag': {'colors': {0: 'warning', 1: 'info', 2: 'info', 8: 'error', 9: 'success'}}},
    'observacao':            {'type': 'MEMO', 'label': 'Observação', 'pos_list': 0, 'width': 40},
}
