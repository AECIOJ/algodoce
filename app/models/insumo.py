from ajsystem.core.extensions import db
from app.constantes import TIPO_INGREDIENTE, UND_LIST


class Insumo(db.Model):
    __tablename__ = "insumos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    und = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, default=0)

    produtos = db.relationship(
        "ProdutoInsumo", backref="insumo", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Insumo {self.nome}>"


Entity = {
    'id':              {'type': 'ID', 'width': 6},
    'nome':            {'type': 'TEXT', 'width': 18, 'mask': '@T'},
    'tipo':            {'type': 'LIST', 'width': 12, 'options': TIPO_INGREDIENTE},
    'und':             {'type': 'LIST', 'label': 'Und', 'width': 8, 'options': UND_LIST, 'required': True},
}
