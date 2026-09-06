from ajsystem.core.extensions import db


class ProducaoInsumo(db.Model):
    __tablename__ = "producao_insumos"

    id = db.Column(db.Integer, primary_key=True)
    producao_id = db.Column(
        db.Integer, db.ForeignKey("producao.id"), nullable=False
    )
    insumo_id = db.Column(
        db.Integer, db.ForeignKey("insumos.id"), nullable=False
    )
    quantidade = db.Column(db.Numeric(10, 3), nullable=False)
    comprado = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    unidade = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, default=0)

    producao = db.relationship("Producao", back_populates="insumos")
    insumo = db.relationship("Insumo", lazy="joined")

    def __repr__(self):
        return f"<ProducaoInsumo p={self.producao_id} i={self.insumo_id}>"
