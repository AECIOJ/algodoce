from ajsystem.core.extensions import db
from ajsystem.core.utils import divide
from app.constantes import UND_LIST, TIPO_INGREDIENTE


class Produto(db.Model):
    __tablename__ = "produtos"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    qtd_minima = db.Column(db.Integer, nullable=False, default=0)
    qtd_receita = db.Column(db.Integer, nullable=False, default=1)
    imagem = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=True)
    categoria = db.relationship("Categoria", backref="produtos")

    insumos = db.relationship(
        "ProdutoInsumo", backref="produto", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Produto {self.nome}>"

    @property
    def preco(self):
        """Preço por unidade: o `valor` corresponde à quantidade `qtd_minima`.
        Campo virtual (derivado) usado como fonte para o item de orçamento."""
        return divide(self.valor, self.qtd_minima)


Entity = {
    'id':          {'type': 'ID', 'width': 6},
    'nome':        {'type': 'TEXT', 'width': 20, 'transform': 'title'},
    'qtd_minima':  {'type': 'INT', 'label': 'Qtd. Mínima', 'min': 0, 'step': 1, 'default': 1},
    'qtd_receita': {'type': 'INT', 'label': 'Qtd. Receita', 'min': 0, 'step': 1, 'default': 1},
    'valor':       {'type': 'NUM', 'label': 'Valor', 'required': True, 'currency': 1},
    'preco':       {'type': 'NUM', 'label': 'Preço', 'currency': 1, 'pos_list': 1,
                    'calc': 'divide(valor, qtd_minima)'},
    'categoria_id': {'type': 'FK', 'label': 'Categoria', 'width': 12},
    'ativo':       {'type': 'BOOL', 'tag': 'boolean'},
    'imagem':      {'type': 'IMAGE'},
    'descricao':   {'type': 'MEMO', 'label': 'Descrição', 'rows': 4, 'pos_list': 2},
}
