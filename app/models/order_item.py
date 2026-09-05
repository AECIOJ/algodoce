from ajsystem.core.extensions import db


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False
    )
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    product = db.relationship("Product", lazy="select")
    order = db.relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem o={self.order_id} p={self.product_id}>"


Entity = {
    'id':              {'type': 'ID'},
    'order_id':        {'type': 'DK'},
    'product_id':      {'type': 'FK', 'label': 'Produto', 'required': True},
    'quantidade':      {'type': 'INT', 'label': 'Qtd', 'required': True},
    'preco_unitario':  {'type': 'NUM', 'label': 'Preço', 'currency': 1},
    'valor':           {'type': 'NUM', 'label': 'Valor', 'currency': 1,
                        'pos_form': 0, 'calc': 'quantidade * preco_unitario'},
    'observacao':      {'type': 'TEXT', 'label': 'Obs'},
}
