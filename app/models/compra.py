from ajsystem.core.extensions import db
from app.constantes import COMPRA_STATUS


class Compra(db.Model):
    __tablename__ = "compras"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    acrescimo = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    desconto = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    status = db.Column(db.Integer, nullable=False, default=0)
    carteira_id = db.Column(db.Integer, db.ForeignKey("carteira.id"), nullable=True)
    pedido_em = db.Column(db.Date, nullable=True)
    faturado_em = db.Column(db.Date, nullable=True)
    cancelado_em = db.Column(db.Date, nullable=True)
    recebido_em = db.Column(db.Date, nullable=True)
    devolvido_em = db.Column(db.Date, nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    fornecedor = db.relationship("Conta", foreign_keys=[fornecedor_id])
    carteira = db.relationship("Carteira", uselist=False)
    items = db.relationship(
        "CompraItem", back_populates="compra",
        foreign_keys="CompraItem.compra_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Compra {self.id}>"

    @property
    def total(self):
        return (self.valor or 0) + (self.acrescimo or 0) - (self.desconto or 0)

    def calc_status(self):
        if self.devolvido_em:
            return 9
        if self.recebido_em:
            return 8
        if self.cancelado_em:
            return 6
        if self.faturado_em and (self.transacao or self.movto):
            return 2
        if self.pedido_em:
            return 1
        status = self.status or 0
        return 0 if status == 2 else status

    def __repr__(self):
        return f"<Compra {self.id}>"


Entity = {
    'id':           {'type': 'ID', 'width': 6},
    'data':         {'type': 'DATA', 'width': 10},
    'fornecedor_id': {'type': 'FK', 'label': 'Fornecedor', 'width': 20},
    'carteira_id':  {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'valor':        {'type': 'NUM', 'currency': 1, 'width': 12},
    'acrescimo':    {'type': 'NUM', 'currency': 1, 'width': 12},
    'desconto':     {'type': 'NUM', 'currency': 1, 'width': 12},
    'total':        {'type': 'NUM', 'currency': 1, 'readonly': True, 'width': 12,
                     'calc': 'valor + acrescimo - desconto'},
    'status':       {'type': 'LIST', 'width': 11, 'options': COMPRA_STATUS,
                     'tag': {'colors': {0: 'warning', 1: 'info', 2: 'info',
                                        6: 'warning', 8: 'success', 9: 'error'}}},
    'pedido_em':    {'type': 'DATA', 'label': 'Pedido em'},
    'faturado_em':  {'type': 'DATA', 'label': 'Faturado em'},
    'cancelado_em': {'type': 'DATA', 'label': 'Cancelado em'},
    'recebido_em':  {'type': 'DATA', 'label': 'Recebido em'},
    'devolvido_em': {'type': 'DATA', 'label': 'Devolvido em'},
    'observacao':   {'type': 'MEMO', 'label': 'Observação', 'width': 40, 'rows':3},
}
