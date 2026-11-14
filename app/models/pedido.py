from datetime import datetime, timezone
from ajsystem.core.extensions import db
from app.extends.constants import STATUS_PEDIDO, FORMINHAS
from app.extends.masks import MVALOR


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    conta_id = db.Column(
        db.Integer, db.ForeignKey("conta.id"), nullable=False
    )
    data = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    previsao_entrega = db.Column(db.DateTime, nullable=True)
    data_fatura = db.Column(db.Date, nullable=True)
    data_cancelado = db.Column(db.Date, nullable=True)
    data_entrega = db.Column(db.Date, nullable=True)
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
        if self.data_entrega:
            return 9
        if self.data_cancelado:
            return 8
        if self.data_fatura and (self.transacao or self.movto):
            return 1
        status = self.status or 0
        return 0 if status == 1 else status


Entity = {
    'id':                    {'type': 'ID', 'width': 6},
    'data':                  {'type': 'DATA_HORA', 'label': 'Data', 'readonly': True},
    'conta_id':             {'type': 'FK', 'label': 'Cliente', 'width': 20, 'required': True},
    'previsao_entrega':      {'type': 'DATA_HORA', 'label': 'Prev. Entrega', 'mask': 'ddd dd/mm/yyyy hh:ii'},
    'data_entrega':          {'type': 'DATA', 'label': 'Entrega', },
    'data_fatura':           {'type': 'DATA', 'label': 'Faturamento', },
    'data_cancelado':        {'type': 'DATA', 'label': 'Cancelamento', },
    'carteira_id':           {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'forminhas':             {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
    'valor':                 {'type': 'NUM', 'width': 10, 'required': True,
                              'mask': MVALOR},
    'acrescimo':             {'type': 'NUM', 'width': 10, 'mask': MVALOR},
    'desconto':              {'type': 'NUM', 'width': 10, 'mask': MVALOR},
    'total':                 {'type': 'NUM', 'readonly': True, 'width': 10,
                              'mask': MVALOR, 'calc': 'valor + acrescimo - desconto'},
    'status':                {'type': 'LIST', 'width': 11, 'options': STATUS_PEDIDO},
    'transacao_id':          {'type': 'INT', 'label': 'Transação', 'calc': lambda row: row.transacao_id},
    'movto_id':              {'type': 'INT', 'label': 'Movimento', 'calc': lambda row: row.movto_id},
    'observacao':            {'type': 'MEMO', 'label': 'Observação', 'width': 40},
}
