from ajsystem.core.extensions import db
from app.constantes import COMPRA_STATUS


class CompraHistorico(db.Model):
    __tablename__ = "compra_historico"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey("compras.id"), nullable=False)
    status = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, nullable=False)
    usuario = db.Column(db.String(100), nullable=True)
    responsavel = db.Column(db.String(100), nullable=True)
    motivo = db.Column(db.Text, nullable=True)

    compra = db.relationship("Compra", back_populates="historicos")

    def __repr__(self):
        return f"<CompraHistorico c={self.compra_id} s={self.status} d={self.data}>"


Entity = {
    'id':          {'type': 'ID'},
    'compra_id':   {'type': 'DK'},
    'status':      {'type': 'LIST', 'options': COMPRA_STATUS},
    'data':        {'type': 'DATA', 'required': True},
    'responsavel': {'type': 'TEXT', 'label': 'Responsável'},
    'motivo':      {'type': 'TEXT', 'label': 'Motivo'},
}
