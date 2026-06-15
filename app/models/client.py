from app.extensions import db


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)

    orders = db.relationship("Order", backref="client", lazy="dynamic")

    def __repr__(self):
        return f"<Client {self.nome}>"
