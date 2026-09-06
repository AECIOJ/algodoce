from ajsystem.core.extensions import db
from app.constantes import UND_LIST, PRODUCAO_ETAPAS


class ProdutoInsumo(db.Model):
    __tablename__ = "produto_insumos"

    produto_id = db.Column(
        db.Integer, db.ForeignKey("produtos.id"), primary_key=True
    )
    insumo_id = db.Column(
        db.Integer, db.ForeignKey("insumos.id"), primary_key=True
    )
    quantidade = db.Column(db.Numeric(10, 3), nullable=False)
    unidade = db.Column(db.String(20), nullable=False, default="un")
    etapas = db.Column(db.String(10), nullable=True)

    def __repr__(self):
        return f"<ProdutoInsumo p={self.produto_id} i={self.insumo_id}>"


Entity = {
    'insumo_id': {'type': 'DK', 'label': 'Insumo'},
    'produto_id':    {'type': 'FK', 'label': 'Produto', 'required': True},
    'quantidade':    {'type': 'NUM'},
    'unidade':       {'type': 'LIST', 'options': UND_LIST},
    'etapas':        {'type': 'MULT10', 'list': PRODUCAO_ETAPAS, 'align': 'center'},
}
