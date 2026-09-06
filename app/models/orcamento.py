from datetime import datetime, timezone
from ajsystem.core.extensions import db
from app.constantes import QUOTE_STATUS, FORMINHAS
from ajsystem.core.utils import add_dias


def _validade_data(q):
    """Data de validade do orçamento = base (renovação ou pedido) + prazo (dias)."""
    if not q:
        return None
    return add_dias(q.data_renovacao or q.data_pedido, q.validade or 3)


class Orcamento(db.Model):
    __tablename__ = "orcamentos"

    id = db.Column(db.Integer, primary_key=True)
    data_pedido = db.Column(
        db.DateTime, nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=True)
    total = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text)
    validade = db.Column(db.Integer, nullable=False, default=3)
    carteira_id = db.Column(db.Integer, db.ForeignKey("carteira.id"), nullable=True)
    data_renovacao = db.Column(db.DateTime, nullable=True)
    forminhas = db.Column(db.Integer, nullable=False, default=0)

    carteira = db.relationship("Carteira", uselist=False)
    pedido = db.relationship("Pedido", foreign_keys=[pedido_id], lazy="joined")
    evento = db.relationship("Evento", back_populates="orcamento", uselist=False, lazy="joined")
    items = db.relationship(
        "OrcamentoItem", back_populates="orcamento",
        foreign_keys="OrcamentoItem.orcamento_id",
        lazy="joined"
    )

    def __repr__(self):
        return f"<Orcamento {self.id}>"


Entity = {
    'id':               {'type': 'ID', 'width': 6},
    'cliente_nome':     {'type': 'TEXT', 'label': 'Cliente', 'required': True, 'width': 20},
    'cliente_telefone': {'type': 'FONE', 'label': 'Telefone', 'required': True},
    'data_pedido':      {'type': 'DATA_HORA', 'label': 'Data',},
    'status':           {'type': 'LIST', 'width': 12, 'options': QUOTE_STATUS,
                         'tag': {'colors': {0: 'warning', 1: 'info', 6: 'success'}}},
    'validade':         {'type': 'INT', 'label': 'Validade (dias)', 'min': 1},
    'validade_data':    {'type': 'DATA_HORA', 'label': 'Válido até', 'calc': _validade_data, 'width': 14, 'pos_form': 2},
    'forminhas':        {'type': 'LIST', 'label': 'Forminhas', 'options': FORMINHAS, 'width': 12},
    'total':            {'type': 'NUM', 'currency': 1, 'width': 12, 'readonly': True},
    'carteira_id':      {'type': 'FK', 'label': 'Pagamento', 'width': 15},
    'pedido_id':        {'type': 'FK', 'label': 'Pedido', 'width': 9,
                        'tag': {'link': 'pedidos.form', 'color': 'info'}},
    'observacao':       {'type': 'MEMO', 'width': 40, 'pos_list': 2},
}
