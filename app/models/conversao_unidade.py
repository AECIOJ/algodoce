from ajsystem.core.extensions import db
from app.constantes import UND_LIST


class ConversaoUnidade(db.Model):
    __tablename__ = "insumo_conversoes"

    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(
        db.Integer, db.ForeignKey("insumos.id"), nullable=False
    )
    und = db.Column(db.String(20), nullable=False)
    fator = db.Column(db.Numeric(10, 6), nullable=False)

    insumo = db.relationship("Insumo", backref="conversoes")

    def __repr__(self):
        return f"<ConversaoUnidade i={self.insumo_id} {self.und}={self.fator}>"


Entity = {
    'id':            {'type': 'ID'},
    'insumo_id': {'type': 'DK', 'label': 'Insumo'},
    'und':         {'type': 'LIST', 'options': UND_LIST, 'required': True},
    'fator':         {'type': 'NUM', 'required': True, 'decimals': 6},
}
