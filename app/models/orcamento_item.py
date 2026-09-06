from ajsystem.core.extensions import db


class OrcamentoItem(db.Model):
    __tablename__ = "orcamento_itens"

    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(
        db.Integer, db.ForeignKey("orcamentos.id"), nullable=False
    )
    produto_id = db.Column(
        db.Integer, db.ForeignKey("produtos.id"), nullable=False
    )
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    produto = db.relationship("Produto", lazy="joined")
    orcamento = db.relationship("Orcamento", back_populates="items")

    def __repr__(self):
        return f"<OrcamentoItem q={self.orcamento_id} p={self.produto_id}>"


Entity = {
    'id':              {'type': 'ID'},
    'orcamento_id':        {'type': 'DK'},
    'produto_id':      {'type': 'FK', 'label': 'Produto', 'required': True},
    'quantidade':      {'type': 'INT', 'label': 'Qtd', 'required': True},
    'preco_unitario':  {'type': 'NUM', 'label': 'Preço', 'currency': 1},
    'valor':           {'type': 'NUM', 'label': 'Valor', 'currency': 1,
                        'pos_form': 0, 'calc': 'quantidade * preco_unitario'},
    'observacao':      {'type': 'TEXT', 'label': 'Obs'},
}
