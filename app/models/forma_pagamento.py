from app.extensions import db


class FormaPagamento(db.Model):
    __tablename__ = "forma_pagamento"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    uso = db.Column(db.Integer, nullable=False, default=1)   # 0=Pedido, 1=Ambos, 2=Compra
    gerar = db.Column(db.Integer, nullable=False, default=0)   # 0=Movimento, 1=Previsao
    prazo_recebimento = db.Column(db.String(100), nullable=True)
    taxa_recebimento = db.Column(db.Numeric(5, 2), nullable=False, default=0)

    def __repr__(self):
        return f"<FormaPagamento {self.nome}>"
