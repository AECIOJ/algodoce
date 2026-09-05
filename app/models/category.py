from ajsystem.core.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    ordem = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Category {self.nome}>"


Entity = {
    'id':    {'type': 'ID', 'width': 6},
    'nome':  {'type': 'TEXT', 'required': True},
    'ordem': {'type': 'INT', 'mask': '999', 'min': 0, 'max': 99},
    'ativo': {'type': 'BOOL'},
}
