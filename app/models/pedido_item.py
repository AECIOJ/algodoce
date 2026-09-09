from ajsystem.core.extensions import db


class PedidoItem(db.Model):
    __tablename__ = "pedido_itens"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), nullable=False
    )
    produto_id = db.Column(
        db.Integer, db.ForeignKey("produtos.id"), nullable=False
    )
    qtd = db.Column(db.Integer, nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    produto = db.relationship("Produto", lazy="select")
    pedido = db.relationship("Pedido", back_populates="items")

    def __repr__(self):
        return f"<PedidoItem o={self.pedido_id} p={self.produto_id}>"


Entity = {
    'id':              {'type': 'ID'},
    'pedido_id':        {'type': 'DK'},
    'produto_id':      {'type': 'FK', 'label': 'Produto', 'required': True},
    'qtd':             {'type': 'INT', 'label': 'Qtd', 'required': True},
    'preco':           {'type': 'NUM', 'label': 'Preço', 'currency': 1},
    'valor':           {'type': 'NUM', 'label': 'Valor', 'currency': 1,
                        'pos_form': 0, 'calc': 'qtd * preco'},
    'observacao':      {'type': 'TEXT', 'label': 'Obs'},
}
