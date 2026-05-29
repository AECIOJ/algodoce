from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    unidade = db.Column(db.String(20), nullable=False, default="cento")
    imagem = db.Column(db.String(255))
    ativo = db.Column(db.Boolean, default=True)

    ingredients = db.relationship(
        "ProductIngredient", backref="product", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.nome}>"
