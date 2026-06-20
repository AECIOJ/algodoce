from app.extensions import db


class Producao(db.Model):
    __tablename__ = "producao"

    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    data_fim = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)
    previsao_de = db.Column(db.Date, nullable=True)
    previsao_ate = db.Column(db.Date, nullable=True)

    insumos = db.relationship(
        "ProducaoInsumo", back_populates="producao",
        lazy="joined", cascade="all, delete-orphan"
    )
    produtos = db.relationship(
        "ProducaoProduto", back_populates="producao",
        lazy="joined", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Producao {self.id} - {self.status}>"
