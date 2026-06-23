from app.extensions import db

class Recurso(db.Model):
    __tablename__ = "recurso"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, server_default="0")
    saldo = db.Column(db.Numeric(12, 2), nullable=False, server_default="0")
    data = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<Recurso {self.nome}>"
