from ajsystem.core.extensions import db


class ProducaoProduto(db.Model):
    __tablename__ = "producao_produtos"

    id = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=False
    )
    pedido_id = db.Column(
        db.Integer, db.ForeignKey("pedidos.id"), nullable=False
    )
    produto_id = db.Column(
        db.Integer, db.ForeignKey("produtos.id"), nullable=False
    )
    qtd = db.Column(db.Integer, nullable=False)
    producao_0 = db.Column(db.Integer, nullable=False, default=0)
    producao_1 = db.Column(db.Integer, nullable=False, default=0)
    producao_2 = db.Column(db.Integer, nullable=False, default=0)

    producao = db.relationship("Producao", back_populates="produtos")
    pedido = db.relationship("Pedido", lazy="joined")
    produto = db.relationship("Produto", lazy="joined")

    def __repr__(self):
        return f"<ProducaoProduto p={self.producao_id} prod={self.produto_id}>"
