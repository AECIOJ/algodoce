from app.extensions import db


class Operacao(db.Model):
    __tablename__ = "operacao"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.Integer, nullable=False, server_default="1")
    pai_id = db.Column(db.Integer, db.ForeignKey("operacao.id"), nullable=True)
    ordem = db.Column(db.Integer, nullable=False, server_default="0")
    fator = db.Column(db.Integer, nullable=False, server_default="1")
    ativa = db.Column(db.Boolean, default=True)

    pai = db.relationship("Operacao", remote_side="Operacao.id", backref="filhos")

    def __repr__(self):
        return f"<Operacao {self.nome}>"
