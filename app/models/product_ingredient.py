from app.extensions import db


class ProductIngredient(db.Model):
    __tablename__ = "product_ingredients"

    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id"), primary_key=True
    )
    ingredient_id = db.Column(
        db.Integer, db.ForeignKey("ingredients.id"), primary_key=True
    )
    quantidade = db.Column(db.Numeric(10, 3), nullable=False)
    unidade = db.Column(db.String(20), nullable=False, default="un")
    etapa_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<ProductIngredient p={self.product_id} i={self.ingredient_id}>"
