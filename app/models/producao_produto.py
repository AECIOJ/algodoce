from app.extensions import db


class ProducaoProduto(db.Model):
    __tablename__ = "producao_produtos"

    id = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=False
    )
    order_id = db.Column(
        db.Integer, db.ForeignKey("orders.id"), nullable=False
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), nullable=False
    )
    quantidade = db.Column(db.Integer, nullable=False)
    producao_0 = db.Column(db.Integer, nullable=False, default=0)
    producao_1 = db.Column(db.Integer, nullable=False, default=0)
    producao_2 = db.Column(db.Integer, nullable=False, default=0)

    producao = db.relationship("Producao", back_populates="produtos")
    order = db.relationship("Order", lazy="joined")
    product = db.relationship("Product", lazy="joined")

    def __repr__(self):
        return f"<ProducaoProduto p={self.producao_id} prod={self.product_id}>"
