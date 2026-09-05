from ajsystem.core.extensions import db
from ajsystem.core.utils import divide
from app.constantes import UND_LIST, TIPO_INGREDIENTE


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    qtd_minima = db.Column(db.Integer, nullable=False, default=0)
    imagem = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    category = db.relationship("Category", backref="products")

    ingredients = db.relationship(
        "ProductIngredient", backref="product", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.nome}>"

    @property
    def preco_unitario(self):
        """Preço por unidade: o `preco` corresponde à quantidade `qtd_minima`.
        Campo virtual (derivado) usado como fonte para o item de orçamento."""
        return divide(self.preco, self.qtd_minima)


Entity = {
    'id':          {'type': 'ID', 'width': 6},
    'nome':        {'type': 'TEXT', 'width': 20, 'transform': 'title'},
    'qtd_minima':  {'type': 'INT', 'label': 'Qtd. Mínima', 'min': 0, 'step': 1, 'default': 1},
    'preco':       {'type': 'NUM', 'label': 'Valor', 'required': True, 'currency': 1},
    'preco_unitario': {'type': 'NUM', 'label': 'Preço', 'currency': 1,
                       'pos_list': 1,
                       'calc': 'divide(preco, qtd_minima)'},
    'category_id': {'type': 'FK', 'label': 'Categoria', 'width': 12},
    'ativo':       {'type': 'BOOL', 'tag': 'boolean'},
    'imagem':      {'type': 'IMAGE'},
    'descricao':   {'type': 'MEMO', 'label': 'Descrição', 'rows': 4, 'pos_list': 2},
}
