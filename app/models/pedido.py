from datetime import datetime, timezone
from ajsystem.core.extensions import db
from app.constantes import STATUS_PEDIDO, FORMINHAS


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(
        db.Integer, db.ForeignKey("conta.id"), nullable=False
    )
    pedido_em = db.Column(
        db.Date, nullable=False,
        default=lambda: datetime.now(timezone.utc).date()
    )
    data_previsao_entrega = db.Column(db.DateTime, nullable=True)
    faturado_em = db.Column(db.Date, nullable=True)
    cancelado_em = db.Column(db.Date, nullable=True)
    entregue_em = db.Column(db.Date, nullable=True)
    observacao = db.Column(db.Text)
    valor = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    acrescimo = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    desconto = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    carteira_id = db.Column(db.Integer, db.ForeignKey("carteira.id"), nullable=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.Integer, nullable=False, default=0)

    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=True
    )
    producao = db.relationship("Producao", foreign_keys=[producao_id], lazy="select")
    orcamento_id = db.Column(
        db.Integer, db.ForeignKey("orcamentos.id"), nullable=True
    )
    orcamento = db.relationship("Orcamento", foreign_keys=[orcamento_id], lazy="select")
    carteira = db.relationship("Carteira", uselist=False)
    evento = db.relationship("Evento", back_populates="pedido", uselist=False, lazy="select")
    items = db.relationship(
        "PedidoItem", back_populates="pedido",
        foreign_keys="PedidoItem.pedido_id",
        lazy="select"
    )

    def __repr__(self):
        return f"<Pedido {self.id} - {self.status}>"

    @property
    def total(self):
        return (self.valor or 0) + (self.acrescimo or 0) - (self.desconto or 0)

    @property
    def transacao_id(self):
        return self.transacao.id if self.transacao else None

    @property
    def movto_id(self):
        return self.movto.id if self.movto else None

    def calc_status(self):
        if self.entregue_em:
            return 9
        if self.cancelado_em:
            return 8
        if self.faturado_em and (self.transacao or self.movto):
            return 1
        status = self.status or 0
        return 0 if status == 1 else status


Entity = {
    'id':                    {'type': 'ID', 'width': 6},
    'conta_id':             {'type': 'FK', 'label': 'Cliente', 'width': 20, 'required': True},
    'pedido_em':             {'type': 'DATA', 'label': 'Pedido em',},
    'data_previsao_entrega': {'type': 'DATA_HORA', 'label': 'Prev. Entrega', 'mask': 'ddd dd/mm/yyyy hh:ii'},
    'entregue_em':           {'type': 'DATA', 'label': 'Entregue em', },
    'faturado_em':           {'type': 'DATA', 'label': 'Faturado em', },
    'cancelado_em':          {'type': 'DATA', 'label': 'Cancelado em', },
    'carteira_id':           {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'forminhas':             {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
    'valor':                 {'type': 'NUM', 'currency': 1, 'width': 10, 'required': True},
    'acrescimo':             {'type': 'NUM', 'currency': 1, 'width': 10},
    'desconto':              {'type': 'NUM', 'currency': 1, 'width': 10},
    'total':                 {'type': 'NUM', 'currency': 1, 'readonly': True, 'width': 10,
                              'calc': 'valor + acrescimo - desconto'},
    'status':                {'type': 'LIST', 'width': 11, 'options': STATUS_PEDIDO},
    'transacao_id':          {'type': 'INT', 'label': 'Transação', 'calc': lambda row: row.transacao_id},
    'movto_id':              {'type': 'INT', 'label': 'Movimento', 'calc': lambda row: row.movto_id},
    'observacao':            {'type': 'MEMO', 'label': 'Observação', 'width': 40},
}
