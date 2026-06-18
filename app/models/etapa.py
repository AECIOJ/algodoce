from app.extensions import db


class Etapa(db.Model):
    __tablename__ = "etapas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<Etapa {self.nome}>"
