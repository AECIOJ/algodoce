from app.extensions import db


class UnitConversion(db.Model):
    __tablename__ = "unit_conversions"

    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(
        db.Integer, db.ForeignKey("ingredients.id"), nullable=False
    )
    unidade = db.Column(db.String(20), nullable=False)
    fator = db.Column(db.Numeric(10, 6), nullable=False)

    ingredient = db.relationship("Ingredient", backref="conversions")

    def __repr__(self):
        return f"<UnitConversion i={self.ingredient_id} {self.unidade}={self.fator}>"
