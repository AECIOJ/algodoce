from app.extensions import db


class Compra(db.Model):
    __tablename__ = "compras"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey("conta.id"), nullable=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    historico = db.Column(db.Text, nullable=True)

    fornecedor = db.relationship("Conta", foreign_keys=[fornecedor_id])
    items = db.relationship(
        "CompraItem", back_populates="compra",
        foreign_keys="CompraItem.compra_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Compra {self.id}>"
