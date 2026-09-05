from ajsystem.core.extensions import db
from app.constantes import TIPO_RECURSO

class Recurso(db.Model):
    __tablename__ = "recurso"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, server_default="0")
    saldo = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    data = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Recurso {self.nome}>"


Entity = {
    'id':    {'type': 'ID', 'width': 7},
    'nome':  {'type': 'TEXT', 'width': 20, 'required': True, 'transform': 'title'},
    'tipo':  {'type': 'LIST', 'width': 12, 'options': TIPO_RECURSO, 'required': True},
    'saldo': {'type': 'NUM', 'label': 'Saldo Inicial', 'width': 12, 'currency': 1},
    'data':  {'type': 'DATA', 'label': 'Balanço', 'width': 12},
}
