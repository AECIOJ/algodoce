from ajsystem.core.extensions import db
from app.extends.constants import STATUS_COMPRA
from app.extends.masks import MVALOR


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

    @property
    def transacao_id(self):
        return self.transacao.id if self.transacao else None

    @property
    def movto_id(self):
        return self.movto.id if self.movto else None

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
    'valor':        {'type': 'NUM', 'width': 12, 'mask': MVALOR},
    'acrescimo':    {'type': 'NUM', 'width': 12, 'mask': MVALOR},
    'desconto':     {'type': 'NUM', 'width': 12, 'mask': MVALOR},
    'total':        {'type': 'NUM', 'readonly': True, 'width': 12,
                     'mask': MVALOR, 'calc': 'valor + acrescimo - desconto'},
    'status':       {'type': 'LIST', 'width': 11, 'options': STATUS_COMPRA},
    'transacao_id': {'type': 'INT', 'label': 'Transação', 'calc': lambda row: row.transacao_id},
    'movto_id':     {'type': 'INT', 'label': 'Movimento', 'calc': lambda row: row.movto_id},
    'pedido_em':    {'type': 'DATA', 'label': 'Pedido em','pos_list': 2},
    'faturado_em':  {'type': 'DATA', 'label': 'Faturado em','pos_list': 2},
    'cancelado_em': {'type': 'DATA', 'label': 'Cancelado em','pos_list': 2},
    'recebido_em':  {'type': 'DATA', 'label': 'Recebido em','pos_list': 2},
    'devolvido_em': {'type': 'DATA', 'label': 'Devolvido em','pos_list': 2},
    'observacao':   {'type': 'MEMO', 'label': 'Observação','pos_list': 2, 'width': 40, 'rows':3},
}
