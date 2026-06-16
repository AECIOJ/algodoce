from app.extensions import db


class Conta(db.Model):
    __tablename__ = "conta"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    cpf = db.Column(db.String(14), nullable=True)
    cnpj = db.Column(db.String(18), nullable=True)
    insc_estadual = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, default=True)
    tipo = db.Column(db.Integer, default=0)

    orders = db.relationship("Order", backref="conta", lazy="dynamic")

    def __repr__(self):
        return f"<Conta {self.nome}>"
