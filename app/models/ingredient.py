from app.extensions import db


class Ingredient(db.Model):
    __tablename__ = "ingredients"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    unidade_medida = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, default=0)

    products = db.relationship(
        "ProductIngredient", backref="ingredient", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Ingredient {self.nome}>"
