from app.extensions import db


class CompraItem(db.Model):
    __tablename__ = "compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(
        db.Integer, db.ForeignKey("compras.id"), nullable=False
    )
    insumo_id = db.Column(
        db.Integer, db.ForeignKey("ingredients.id"), nullable=False
    )
    quantidade = db.Column(db.Numeric(12, 3), nullable=False)
    preco = db.Column(db.Numeric(12, 2), nullable=False)

    compra = db.relationship("Compra", back_populates="items")
    insumo = db.relationship("Ingredient", lazy="joined")

    def __repr__(self):
        return f"<CompraItem c={self.compra_id} i={self.insumo_id}>"
