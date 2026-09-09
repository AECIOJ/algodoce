from ajsystem.core.extensions import db


class CompraItem(db.Model):
    __tablename__ = "compra_itens"

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(
        db.Integer, db.ForeignKey("compras.id"), nullable=False
    )
    insumo_id = db.Column(
        db.Integer, db.ForeignKey("insumos.id"), nullable=False
    )
    qtd = db.Column(db.Numeric(12, 3), nullable=False)
    preco = db.Column(db.Numeric(12, 2), nullable=False)

    compra = db.relationship("Compra", back_populates="items")
    insumo = db.relationship("Insumo", lazy="joined")

    def __repr__(self):
        return f"<CompraItem c={self.compra_id} i={self.insumo_id}>"


Entity = {
    'id':           {'type': 'ID'},
    'compra_id':    {'type': 'DK'},
    'insumo_id':    {'type': 'FK', 'label': 'Insumo', 'required': True},
    'qtd':          {'type': 'NUM', 'label': 'Qtd', 'required': True},
    'preco':        {'type': 'NUM', 'label': 'Preço', 'required': True, 'currency': 1},
    'valor':        {'type': 'NUM', 'label': 'Valor', 'currency': 1,
                     'pos_form': 0, 'calc': 'qtd * preco'},
}
